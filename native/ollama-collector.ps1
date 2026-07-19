# Headroom native collector: Ollama (Windows, zero dependencies).
# Usage: powershell -ExecutionPolicy Bypass -File ollama-collector.ps1 [model] [host]
param(
  [string]$Model = "gemma3n:e2b",
  [string]$Ollama = "http://localhost:11434"
)
$ErrorActionPreference = "Stop"
$Prompt = "Write a detailed, factual explanation of how memory bandwidth limits the decoding speed of large language models on consumer hardware."
$Runs = 3; $NumPredict = 256

$tags = Invoke-RestMethod "$Ollama/api/tags"
$size = ($tags.models | Where-Object { $_.name -eq $Model -or $_.model -eq $Model } | Select-Object -First 1).size
$ver = (Invoke-RestMethod "$Ollama/api/version").version

$decode = @(); $prefill = @(); $receipts = @()
for ($i = 1; $i -le $Runs; $i++) {
  $body = @{ model = $Model; prompt = $Prompt; stream = $false; options = @{ num_predict = $NumPredict } } | ConvertTo-Json
  $r = Invoke-RestMethod -Method Post -Uri "$Ollama/api/generate" -Body $body -ContentType "application/json" -TimeoutSec 600
  $d = $r.eval_count / ($r.eval_duration / 1e9)
  $decode += $d
  if ($r.prompt_eval_duration) { $prefill += $r.prompt_eval_count / ($r.prompt_eval_duration / 1e9) }
  $receipts += @{ probe = "generate run $i"; result = ("{0:N1} tok/s decode ({1} tokens)" -f $d, $r.eval_count); gate = "ollama eval_count/eval_duration" }
  Write-Host ("run {0}: {1:N1} tok/s" -f $i, $d)
}
$median = { param($a) ($a | Sort-Object)[[math]::Floor($a.Count / 2)] }

$out = [ordered]@{
  tool = "headroom"; collector = "ollama"; version = "0.1.0"
  ts = (Get-Date).ToUniversalTime().ToString("o")
  device = @{ ollama = $ver; model = $Model; modelBytes = $size }
  method = @{ runs = $Runs; num_predict = $NumPredict; timing = "ollama eval_duration medians, warm model"; note = "first run may include load; inspect per-run receipts" }
  score = @{
    decode_toks_median = [math]::Round((& $median $decode), 1)
    decode_toks_all = @($decode | ForEach-Object { [math]::Round($_, 1) })
    prefill_toks_median = if ($prefill.Count) { [math]::Round((& $median $prefill), 1) } else { $null }
  }
  receipts = $receipts
}
$path = "headroom-receipt-ollama.json"
$out | ConvertTo-Json -Depth 6 | Set-Content $path -Encoding UTF8
Write-Host "wrote $path"
