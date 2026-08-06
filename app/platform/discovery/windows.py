"""Discovers programs from the Start Menu and the registry's
Uninstall/App Paths keys, via a PowerShell script that also
extracts each one's icon."""

from __future__ import annotations

import json
import os
import subprocess

from ...infra import log

_JUNK_TOKENS = ("uninstall", "удал", "readme", "read me", "help", "документац",
                "documentation", "release notes", "website", "на сайт", "лиценз",
                "license", "manual", "руководств", "support", "поддержк")

_WIN_NAME_JUNK = ("node.js", "command prompt", "командная строка", "stack builder",
                  "recovery drive", "диск восстановлен", "verifier", "debugger",
                  "redistributable", "runtime", "hotfix", "update for", "sdk ",
                  "web platform", "webview")

def _looks_like_junk(name: str) -> bool:
    n = name.lower()
    return any(tok in n for tok in _JUNK_TOKENS)

def _is_windows_system(name: str, path: str) -> bool:
    p = (path or "").lower().replace("/", "\\")
    if "\\windows\\" in f"\\{p}" or p.startswith(os.environ.get("SystemRoot", "c:\\windows").lower()):
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
'''

_WIN_PS = _PS_ICON_FUNCS + r'''
$sh=New-Object -ComObject WScript.Shell
$out=New-Object System.Collections.ArrayList
function Add-App($n,$p,$s){ if(-not $n -or -not $p){ return }; if($p.ToLower() -like '*\windows\*'){ return }; $ic=Save-Icon $p; [void]$out.Add([PSCustomObject]@{name="$n";path="$p";icon=$ic;src="$s"}) }

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
    $icon=$pr.DisplayIcon
    if($icon){ $exe=($icon -split ',')[0].Trim('"'); if($exe -and $exe.ToLower().EndsWith('.exe') -and (Test-Path -LiteralPath $exe)){ Add-App $pr.DisplayName $exe 'registry' } }
  }
}
$aps=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths')
foreach($k in $aps){
  Get-ChildItem -LiteralPath $k 2>$null | ForEach-Object {
    $p=(Get-Item -LiteralPath $_.PSPath).GetValue(''); if($p){ $p=$p.Trim('"') }
    if($p -and $p.ToLower().EndsWith('.exe') -and (Test-Path -LiteralPath $p)){ Add-App ([System.IO.Path]::GetFileNameWithoutExtension($p)) $p 'registry' }
  }
}
$out | ConvertTo-Json -Compress
'''

_WIN_ICON_ONE_PS = _PS_ICON_FUNCS + r'''
$r=Save-Icon __EXE__
if($r){ Write-Output $r }
'''

def _run_powershell(script: str, timeout: int = 60):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
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
        src = x.get("src") if x.get("src") in ("startmenu", "registry") else "registry"
        apps.append({"name": name, "path": path, "icon": x.get("icon"),
                     "icon_fit": "contain", "source": src})
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
