"""Discovers programs from the Start Menu and the registry's
Uninstall/App Paths keys, via a PowerShell script that also
extracts each one's icon."""

from __future__ import annotations

import json
import ntpath
import os
import re
import subprocess
import sys

from ...infra import log

_JUNK_TOKENS = ("uninstall", "удал", "readme", "read me", "help", "документац",
                "documentation", "release notes", "website", "на сайт", "лиценз",
                "license", "manual", "руководств", "support", "поддержк")

_WIN_NAME_JUNK = ("node.js", "command prompt", "командная строка", "stack builder",
                  "recovery drive", "диск восстановлен", "verifier", "debugger",
                  "redistributable", "runtime", "hotfix", "update for", "sdk ",
                  "web platform", "webview")

# Matched as whole words, so "Rockstar Games SDK" is caught where the "sdk "
# substring above only catches an SDK followed by something else.
_JUNK_NAME_WORDS = frozenset((
    "sdk", "runtime", "redistributable", "redist", "hotfix", "framework",
    "verifier", "debugger", "webview", "webview2", "driver", "drivers",
    "prerequisites", "bootstrapper",
))

# Folders that only ever hold installer payloads, shared plumbing or OS
# components. Every one of these produced a visible false positive: WiX keeps
# installer bundles in Package Cache forever (so a program's *installer*
# offered itself alongside the program), Common Files holds things like
# TabTip, and Windows Mail's wab/wabmig sit outside \Windows\ despite being
# as internal as anything in it.
_JUNK_DIRS = (
    "\\package cache\\",
    "\\common files\\",
    "\\windows mail\\",
    "\\windowsapps\\",
    "\\microsoft shared\\",
    "\\installer\\",
    "\\assembly\\",
    "\\$recycle.bin\\",
)

# The Office suite drops dozens of internal tools next to the real programs
# in the same Office16 folder — SKYPESERVER, MSOXMLED, MSOSYNC and friends.
# Naming the handful of actual applications is shorter and safer than trying
# to enumerate the rest.
_OFFICE_APPS = frozenset((
    "winword.exe", "excel.exe", "powerpnt.exe", "outlook.exe", "msaccess.exe",
    "onenote.exe", "mspub.exe", "visio.exe", "winproj.exe", "lync.exe",
    "teams.exe", "msteams.exe", "groove.exe",
))

_JUNK_EXE_PREFIXES = ("unins", "uninstall", "setup", "install", "remove", "repair")

_JUNK_EXE_PARTS = ("uninstall", "installer", "crashhandler", "crashreport",
                   "crashpad", "vcredist", "vc_redist", "dxsetup", "redist",
                   "prereq", "bootstrap", "elevate", "updater")


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-zа-яё0-9.+]+", (text or "").lower()))


def _looks_like_junk(name: str) -> bool:
    n = name.lower()
    if any(tok in n for tok in _JUNK_TOKENS):
        return True
    return bool(_words(name) & _JUNK_NAME_WORDS)


def _is_junk_target(path: str) -> bool:
    """Whether the executable itself gives the entry away as not-a-program.

    Filtering on the registry's DisplayName alone let plenty through: Steam's
    entry is named "Steam" but points at uninstall.exe, and an installer
    bundle cached under Package Cache carries the real product's name. The
    path is the honest signal.
    """
    p = (path or "").lower().replace("/", "\\")
    if not p:
        return False
    if any(d in p for d in _JUNK_DIRS):
        return True
    if "\\microsoft office\\" in p and ntpath.basename(p) not in _OFFICE_APPS:
        return True
    base = ntpath.basename(p)
    stem = base[:-4] if base.endswith(".exe") else base
    if stem.startswith(_JUNK_EXE_PREFIXES):
        return True
    return any(part in stem for part in _JUNK_EXE_PARTS)


def _is_windows_system(name: str, path: str) -> bool:
    p = (path or "").lower().replace("/", "\\")
    if "\\windows\\" in f"\\{p}" or p.startswith(os.environ.get("SystemRoot", "c:\\windows").lower()):
        return True
    if _is_junk_target(path):
        return True
    n = (name or "").lower()
    if _looks_like_junk(name) or any(t in n for t in _WIN_NAME_JUNK):
        return True
    return False

_PS_ICON_FUNCS = r'''
$ErrorActionPreference='SilentlyContinue'
try{[Console]::OutputEncoding=[System.Text.Encoding]::UTF8}catch{}
$OutputEncoding=[System.Text.Encoding]::UTF8
$cache=__CACHE__
Add-Type -AssemblyName System.Drawing
$script:CentBig=$false
try {
  Add-Type -ReferencedAssemblies 'System.Drawing' -TypeDefinition @"
using System;using System.Runtime.InteropServices;using System.Drawing;
public class CentIcon {
 [DllImport("user32.dll")] public static extern int PrivateExtractIcons(string p,int i,int cx,int cy,IntPtr[] h,int[] id,int n,int f);
 [DllImport("user32.dll")] public static extern bool DestroyIcon(IntPtr h);
 public static Bitmap Get(string p,int s){ IntPtr[] h=new IntPtr[1]; int[] id=new int[1]; int r=PrivateExtractIcons(p,0,s,s,h,id,1,0); if(r>0 && h[0]!=IntPtr.Zero){ Icon ic=Icon.FromHandle(h[0]); Bitmap b=new Bitmap(ic.ToBitmap()); DestroyIcon(h[0]); return b; } return null; } }
"@
  $script:CentBig=$true
} catch { $script:CentBig=$false }
function Md5($s){ $m=[System.Security.Cryptography.MD5]::Create(); (($m.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($s.ToLower())))|ForEach-Object{$_.ToString('x2')}) -join '' }
function Save-Icon($exe){
  if(-not $cache){ return $null }
  if(-not (Test-Path -LiteralPath $exe)){ return $null }
  $f=Join-Path $cache ((Md5 $exe)+'_256.png')
  if(Test-Path -LiteralPath $f){ return $f }
  $bmp=$null
  if($script:CentBig){ try{ $bmp=[CentIcon]::Get($exe,256) }catch{ $bmp=$null } }
  if(-not $bmp){ try{ $ic=[System.Drawing.Icon]::ExtractAssociatedIcon($exe); if($ic){ $bmp=$ic.ToBitmap() } }catch{ $bmp=$null } }
  if($bmp){ try{ $bmp.Save($f,[System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose(); return $f }catch{} }
  return $null
}
# A Store app has no .exe to pull an icon from — PrivateExtractIcons/
# ExtractAssociatedIcon above need a real PE file. Its own package carries a
# ready-made PNG in AppxManifest.xml instead, so this reads the manifest and
# copies that logo into the cache rather than "extracting" anything.
function Resolve-StoreAsset($dir,$rel){
  $full=Join-Path $dir $rel
  if(Test-Path -LiteralPath $full){ return $full }
  $folder=Split-Path $full -Parent
  if(-not (Test-Path -LiteralPath $folder)){ return $null }
  $stem=[System.IO.Path]::GetFileNameWithoutExtension($rel)
  $ext=[System.IO.Path]::GetExtension($rel)
  $found=@(Get-ChildItem -LiteralPath $folder -Filter "$stem*$ext" -File 2>$null)
  if($found.Count -eq 0){ return $null }
  # Scaled/qualified variants sit alongside the bare name Manifest names
  # (AppIcon.scale-200.png, ...targetsize-256_altform-unplated.png); prefer
  # an unplated (no colored backplate) one, then the largest file.
  $best=$found | Sort-Object -Property @{Expression={$_.Name -notmatch 'unplated'}},
                                       @{Expression='Length';Descending=$true} | Select-Object -First 1
  return $best.FullName
}
function Save-StoreIcon($family,$appId){
  if(-not $cache -or -not $family){ return $null }
  $f=Join-Path $cache ((Md5 "store:$family!$appId")+'_store.png')
  if(Test-Path -LiteralPath $f){ return $f }
  try{
    $pkg=Get-AppxPackage -PackageFamilyName $family -ErrorAction SilentlyContinue | Select-Object -First 1
    if(-not $pkg -or -not $pkg.InstallLocation){ return $null }
    $manifestPath=Join-Path $pkg.InstallLocation 'AppxManifest.xml'
    if(-not (Test-Path -LiteralPath $manifestPath)){ return $null }
    [xml]$manifest=Get-Content -LiteralPath $manifestPath -Raw
    $ns=New-Object System.Xml.XmlNamespaceManager($manifest.NameTable)
    $ns.AddNamespace('a',$manifest.DocumentElement.NamespaceURI)
    $ns.AddNamespace('uap','http://schemas.microsoft.com/appx/manifest/uap/windows10')
    $logoRel=$null
    $app=$manifest.SelectSingleNode("//a:Applications/a:Application[@Id='$appId']",$ns)
    if($app){
      $ve=$app.SelectSingleNode('uap:VisualElements',$ns)
      if($ve){
        $logoRel=$ve.GetAttribute('Square150x150Logo')
        if(-not $logoRel){ $logoRel=$ve.GetAttribute('Square44x44Logo') }
      }
    }
    if(-not $logoRel){
      $logoNode=$manifest.SelectSingleNode('//a:Properties/a:Logo',$ns)
      if($logoNode){ $logoRel=$logoNode.InnerText }
    }
    if(-not $logoRel){ return $null }
    $src=Resolve-StoreAsset $pkg.InstallLocation $logoRel
    if(-not $src){ return $null }
    Copy-Item -LiteralPath $src -Destination $f -Force
    return $f
  }catch{ return $null }
}
'''

_WIN_PS = _PS_ICON_FUNCS + r'''
$sh=New-Object -ComObject WScript.Shell
$out=New-Object System.Collections.ArrayList
function Add-App($n,$p,$s){ if(-not $n -or -not $p){ return }; if($p.ToLower() -like '*\windows\*'){ return }; $ic=Save-Icon $p; [void]$out.Add([PSCustomObject]@{name="$n";path="$p";icon=$ic;src="$s"}) }
function Add-Store($n,$id){
  if(-not $n -or -not $id){ return }
  $parts=$id -split '!',2
  $family=$parts[0]
  $appId=if($parts.Count -gt 1){ $parts[1] } else { 'App' }
  $ic=Save-StoreIcon $family $appId
  [void]$out.Add([PSCustomObject]@{name="$n";path="shell:AppsFolder\$id";icon=$ic;src='store'})
}

# An Uninstall entry without a usable DisplayIcon still knows where it was
# installed, so fall back to the most plausible executable in that folder
# instead of dropping the program entirely — plenty of installers point
# DisplayIcon at an .ico, or set no icon at all.
$rootish=@('','\','c:\','c:\program files','c:\program files (x86)','c:\windows','c:\users')
function Best-Exe($dir,$name){
  if(-not $dir){ return $null }
  $dir=$dir.Trim('"').TrimEnd('\')
  if($rootish -contains $dir.ToLower()){ return $null }
  if(-not (Test-Path -LiteralPath $dir)){ return $null }
  $files=@(Get-ChildItem -LiteralPath $dir -Filter *.exe -File 2>$null)
  if($files.Count -eq 0){ $files=@(Get-ChildItem -LiteralPath $dir -Filter *.exe -File -Recurse -Depth 1 2>$null) }
  if($files.Count -eq 0){ return $null }
  $ranked=@($files | Sort-Object Length -Descending)
  $toks=@([regex]::Matches($name.ToLower(),'[a-z0-9]+') | ForEach-Object { $_.Value } | Where-Object { $_.Length -ge 3 })
  foreach($f in $ranked){
    $stem=[System.IO.Path]::GetFileNameWithoutExtension($f.Name).ToLower()
    foreach($t in $toks){ if($stem.Contains($t)){ return $f.FullName } }
  }
  return $ranked[0].FullName
}

$menus=@(__DIRS__)
foreach($d in $menus){
  Get-ChildItem -LiteralPath $d -Recurse -Filter *.lnk 2>$null | ForEach-Object {
    $t=$sh.CreateShortcut($_.FullName); $p=$t.TargetPath
    if($p -and $p.ToLower().EndsWith('.exe') -and (Test-Path -LiteralPath $p)){ Add-App $_.BaseName $p 'startmenu' }
  }
}
$uks=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall')
foreach($k in $uks){
  Get-ChildItem -LiteralPath $k 2>$null | ForEach-Object {
    $pr=Get-ItemProperty -LiteralPath $_.PSPath 2>$null
    if(-not $pr.DisplayName){ return }
    if($pr.SystemComponent -eq 1){ return }
    $exe=$null
    $icon=$pr.DisplayIcon
    if($icon){ $c=($icon -split ',')[0].Trim('"'); if($c -and $c.ToLower().EndsWith('.exe') -and (Test-Path -LiteralPath $c)){ $exe=$c } }
    if(-not $exe){ $exe=Best-Exe $pr.InstallLocation $pr.DisplayName }
    if($exe){ Add-App $pr.DisplayName $exe 'registry' }
  }
}
$aps=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths')
foreach($k in $aps){
  Get-ChildItem -LiteralPath $k 2>$null | ForEach-Object {
    $p=(Get-Item -LiteralPath $_.PSPath).GetValue(''); if($p){ $p=$p.Trim('"') }
    if($p -and $p.ToLower().EndsWith('.exe') -and (Test-Path -LiteralPath $p)){ Add-App ([System.IO.Path]::GetFileNameWithoutExtension($p)) $p 'registry' }
  }
}
# Store apps live nowhere on disk that the passes above can see. Get-StartApps
# lists what the Start menu shows; a UWP entry is the one whose AppID carries
# the package-family "!" separator, and it launches through the shell.
$sysapp=@('microsoft.windows.','microsoftwindows.','windows.immersivecontrolpanel',
          'microsoft.aad','microsoft.account','microsoft.creddialoghost','microsoft.ecapp',
          'microsoft.lockapp','microsoft.bioenrollment','microsoft.asynctextservice',
          'microsoft.xboxgamecallableui','microsoft.sechealthui')
try{
  Get-StartApps 2>$null | ForEach-Object {
    $id=$_.AppID
    if($id -and $id.Contains('!')){
      $low=$id.ToLower()
      $skip=$false
      foreach($s in $sysapp){ if($low.StartsWith($s)){ $skip=$true } }
      if(-not $skip){ Add-Store $_.Name $id }
    }
  }
}catch{}
$out | ConvertTo-Json -Compress
'''

_WIN_ICON_ONE_PS = _PS_ICON_FUNCS + r'''
$r=Save-Icon __EXE__
if($r){ Write-Output $r }
'''

def _powershell_exe() -> str:
    """Path to the *native* PowerShell, even when this process is 32-bit.

    A 32-bit build launching plain "powershell" gets silently handed the
    32-bit copy from SysWOW64 by Windows' file-system redirector — and that
    32-bit powershell.exe is then itself subject to *registry* redirection,
    so every HKLM query below, even the un-prefixed "SOFTWARE\\..." one that
    is supposed to be the 64-bit view, comes back mapped into WOW6432Node.
    A native 64-bit install that only ever wrote to the true
    HKLM\\SOFTWARE\\...\\Uninstall — a system-wide VS Code, among others —
    is invisible to it despite every registry path in the script looking
    correct. %windir%\\Sysnative is the redirector's own escape hatch: the
    path exists only from a 32-bit process and always resolves to the real
    (64-bit) System32, sidestepping the problem instead of trying to work
    around registry redirection from inside the script.
    """
    if sys.maxsize > 2**32 or os.name != "nt":
        return "powershell"
    sysnative = os.path.join(os.environ.get("windir", r"C:\Windows"),
                             "Sysnative", "WindowsPowerShell", "v1.0", "powershell.exe")
    return sysnative if os.path.isfile(sysnative) else "powershell"


def _run_powershell(script: str, timeout: int = 60):
    return subprocess.run([_powershell_exe(), "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, creationflags=0x08000000)

def _ps_literal(value: str | None) -> str:
    if not value:
        return "$null"
    return "'" + value.replace("'", "''") + "'"

def _discover_windows(icon_cache: str | None) -> list[dict]:
    prog_data = os.environ.get("ProgramData", r"C:\ProgramData")
    appdata = os.environ.get("APPDATA", "")
    dirs = [os.path.join(prog_data, r"Microsoft\Windows\Start Menu\Programs")]
    if appdata:
        dirs.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"))
    dirs = [d for d in dirs if os.path.isdir(d)]
    dir_list = ",".join(_ps_literal(d) for d in dirs)

    ps = _WIN_PS.replace("__DIRS__", dir_list).replace("__CACHE__", _ps_literal(icon_cache))
    res = _run_powershell(ps, timeout=90)
    out = (res.stdout or "").strip()
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]

    apps = []
    for x in data:
        name, path = x.get("name"), x.get("path")
        if not name or not path or _is_windows_system(name, path):
            continue
        src = x.get("src") if x.get("src") in ("startmenu", "registry", "store") else "registry"
        apps.append({"name": name, "path": path, "icon": x.get("icon"),
                     "icon_fit": "contain", "source": src,
                     "sub": "Microsoft Store" if src == "store" else ""})
    return apps

def _win_extract_one(path: str, icon_cache: str) -> str | None:
    ps = _WIN_ICON_ONE_PS.replace("__CACHE__", _ps_literal(icon_cache)).replace(
        "__EXE__", _ps_literal(path))
    try:
        res = _run_powershell(ps, timeout=25)
    except Exception:
        log.exception("_win_extract_one powershell fail %s", path)
        return None
    out = (res.stdout or "").strip().splitlines()
    out = out[-1].strip() if out else ""
    return out if out and os.path.exists(out) else None
