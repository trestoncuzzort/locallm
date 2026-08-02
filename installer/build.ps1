<#
build.ps1 - compile "Install locallm.exe" from Bootstrap.cs.

Uses csc.exe from the .NET Framework that ships with Windows, so a release can
be built on any Windows machine with nothing installed. The output is a single
native executable to attach to a GitHub release.

    powershell -ExecutionPolicy Bypass -File installer\build.ps1
#>
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$src  = Join-Path $here 'Bootstrap.cs'
$out  = Join-Path $here 'Install_locallm.exe'

# Newest installed Framework compiler. Pinning a version would break on a
# machine that has a different one, and this file exists so a build needs
# nothing installed.
$csc = Get-ChildItem 'C:\Windows\Microsoft.NET\Framework64\v*\csc.exe' -ErrorAction SilentlyContinue |
       Sort-Object FullName -Descending | Select-Object -First 1
if (-not $csc) {
    throw "csc.exe not found under C:\Windows\Microsoft.NET\Framework64. This machine has no .NET Framework compiler."
}

if (-not (Test-Path $src)) { throw "missing source: $src" }
if (Test-Path $out) { Remove-Item $out -Force }

Write-Host "compiler : $($csc.FullName)"
Write-Host "source   : $src"

# /platform:anycpu so one binary runs on 32- and 64-bit Windows.
# /win32icon is deliberately omitted -- there is no icon asset in the repo, and
# referencing one that does not exist would break the build for anyone else.
& $csc.FullName /nologo /target:exe /platform:anycpu /optimize+ `
    "/out:$out" $src
if ($LASTEXITCODE -ne 0) { throw "csc failed with exit code $LASTEXITCODE" }

if (-not (Test-Path $out)) { throw "csc reported success but produced no file" }

$size = [math]::Round((Get-Item $out).Length / 1KB, 1)
Write-Host ""
Write-Host "built    : $out"
Write-Host "size     : $size KB"
Write-Host ""
Write-Host "Attach that file to a GitHub release. Users download it and run it."
