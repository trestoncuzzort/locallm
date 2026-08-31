# overnight.ps1 — self-contained autonomous overnight loop for srlm-forge.
# Runs entirely on LOCAL Ollama: zero cloud tokens, no unsupervised cloud agent.
# Each round: forge generates+dedups preference pairs; every Nth round the eval
# ruler is scored; progress is git-committed for revertibility.
#
# Ping model (as requested): before each phase it writes a signal file so the two
# roles "ping" each other -
#   council\ping_executor  -> generate/executor phase is live
#   council\ping_council    -> eval/critique phase is live
#
# STOP: create the file  C:\Users\t\Projects\srlm-forge\council\STOP  to end cleanly.
# Time cap: -MaxHours (default 9). Kill by hand: Stop-Process on the pwsh running this.

param(
  [int]$MaxHours = 9,
  [int]$SleepSeconds = 20,
  [int]$EvalEvery = 5,
  [int]$RepairEvery = 3
)

$ErrorActionPreference = 'Continue'
$root    = 'C:\Users\t\Projects\srlm-forge'
$council = Join-Path $root 'council'
$py      = 'C:\Python314\python.exe'
$log     = Join-Path $council 'overnight.log'
$status  = Join-Path $council 'overnight_status.txt'
$stop    = Join-Path $council 'STOP'
New-Item -ItemType Directory -Force $council | Out-Null

function Log($m) {
  $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  "$ts  $m" | Out-File -FilePath $log -Append -Encoding utf8
}
function Pairs {
  $pp = Join-Path $root 'data\dpo_pairs.jsonl'
  if (Test-Path $pp) { (Get-Content $pp | Measure-Object -Line).Lines } else { 0 }
}
function RepairPairs {
  $rp = Join-Path $root 'data\repair_pairs.jsonl'
  if (Test-Path $rp) { (Get-Content $rp | Measure-Object -Line).Lines } else { 0 }
}

# Make sure Ollama is serving.
try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 5 | Out-Null }
catch {
  $exe = Get-ChildItem "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -EA SilentlyContinue |
         Select-Object -First 1 -ExpandProperty FullName
  if ($exe) { Start-Process $exe 'serve' -WindowStyle Hidden; Start-Sleep 5 }
}

$deadline = (Get-Date).AddHours($MaxHours)
$startPairs = Pairs
Log "=== overnight start | deadline=$deadline | start_pairs=$startPairs ==="

$round = 0
while ((Get-Date) -lt $deadline) {
  if (Test-Path $stop) { Log "STOP file present -> exiting"; break }
  $round++

  # ---- executor/generate phase ----
  "round $round | $(Get-Date -Format o) | executor: forge generate" | Set-Content (Join-Path $council 'ping_executor')
  Log "round $round : forge generate"
  & $py (Join-Path $root 'forge.py') *>> $log

  # ---- periodic council/eval phase ----
  if ($round % $EvalEvery -eq 0) {
    "round $round | $(Get-Date -Format o) | council: eval ruler" | Set-Content (Join-Path $council 'ping_council')
    Log "round $round : eval ruler"
    & $py (Join-Path $root 'eval.py') *>> $log
  }

  # ---- periodic repair phase: mine current failures into pairs ----
  if ($round % $RepairEvery -eq 0) {
    "round $round | $(Get-Date -Format o) | executor: repair (failure mining)" | Set-Content (Join-Path $council 'ping_executor')
    Log "round $round : repair (failure mining)"
    & $py (Join-Path $root 'repair.py') *>> $log
  }

  $p = Pairs
  $hb = "heartbeat $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | round=$round | total_pairs=$p | repair_pairs=$(RepairPairs) | gained=$([int]$p - [int]$startPairs)"
  $hb | Set-Content $status
  Log "round $round done : total_pairs=$p"

  # revertible snapshot
  git -C $root add -A 2>$null | Out-Null
  git -C $root commit -m "overnight round ${round}: pairs=$p" 2>$null | Out-Null

  Start-Sleep -Seconds $SleepSeconds
}

Log "=== overnight end | rounds=$round | final_pairs=$(Pairs) ==="
