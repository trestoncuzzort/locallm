# finish_adapter3.ps1 — wait for retrain3, export it, serve it, then evaluate it
# interleaved against a same-session null. One script so the whole chain runs
# unattended and every stage checks the stage before it rather than assuming.

$ErrorActionPreference = "Stop"
$repo = "C:\Users\Kingo\source\srlm-forge"
Set-Location $repo
$py = ".\.venv-train\Scripts\python.exe"
$env:SRLM_LLAMA_CPP = "C:\AgentVault\llama.cpp"
$env:Path += ";C:\Users\Kingo\AppData\Local\Programs\Ollama"

function Say($m) { "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m }

# ---- 1. wait for training -------------------------------------------------
Say "waiting for retrain3"
while ($true) {
    $log = Get-Content "poscontrol\retrain3.log" -Raw -ErrorAction SilentlyContinue
    if ($log -match "adapter saved to") { Say "training done"; break }
    if ($log -match "Traceback|Error:") { Say "TRAINING FAILED"; Get-Content poscontrol\retrain3.log -Tail 10; exit 1 }
    if (-not (Get-Process -Id 51728 -ErrorAction SilentlyContinue)) {
        Say "training process gone without a save line"; Get-Content poscontrol\retrain3.log -Tail 10; exit 1
    }
    Start-Sleep -Seconds 30
}

# ---- 2. export to GGUF ----------------------------------------------------
Say "exporting"
& $py export_adapter.py --adapter poscontrol\adapter_replication3 `
    --base-tag llama3:8b-instruct-q4_K_M --name llama3-forged-rep3 `
    --outdir poscontrol\adapter_replication3\export 2>&1 |
    Select-String 'MATCH|FAILED|not found' | ForEach-Object { Say $_.Line.Trim() }

$gguf = "poscontrol\adapter_replication3\export\adapter.gguf"
if (-not (Test-Path $gguf)) { Say "GGUF MISSING — stopping"; exit 1 }
$h = (Get-FileHash $gguf -Algorithm SHA256).Hash.Substring(0, 24).ToLower()
Say "rep3 gguf $h"

# distinctness check: a third adapter identical to an earlier one would mean the
# run did not actually retrain, and every downstream number would be a lie.
foreach ($prior in @("poscontrol\adapter_replication\export\adapter.gguf",
                     "poscontrol\adapter_replication2\export\adapter.gguf")) {
    if (Test-Path $prior) {
        $ph = (Get-FileHash $prior -Algorithm SHA256).Hash.Substring(0, 24).ToLower()
        if ($ph -eq $h) { Say "FATAL: rep3 gguf identical to $prior"; exit 1 }
    }
}
Say "rep3 is distinct from rep1 and rep2"

# ---- 3. serve -------------------------------------------------------------
$G = "$repo\poscontrol\adapter_replication3\export"
Set-Content "$G\Modelfile.rep3" "FROM llama3:8b-instruct-q4_K_M`nADAPTER $G\adapter.gguf" -Encoding ascii
ollama create llama3-forged-rep3 -f "$G\Modelfile.rep3" 2>&1 | Select-Object -Last 1 | ForEach-Object { Say $_ }
Set-Content "$G\Modelfile.null3" "FROM llama3:8b-instruct-q4_K_M" -Encoding ascii
ollama create ctl-null3 -f "$G\Modelfile.null3" 2>&1 | Select-Object -Last 1 | ForEach-Object { Say $_ }

# ---- 4. evaluate, interleaved against a same-session null -----------------
Say "evaluating rep3 vs ctl-null3, 15 rounds interleaved"
& $py poscontrol\run_interleaved.py --rounds 15 --arms llama3-forged-rep3 ctl-null3 2>&1 |
    Select-String 'round |DONE:|ABORTING' | Select-Object -Last 4 | ForEach-Object { Say $_.Line.Trim() }

Say "COMPLETE"
