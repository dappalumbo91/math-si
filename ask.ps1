param(
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$Words
)

$prompt = $Words -join " "
$body = @{
    model    = "gemma4:latest"
    prompt   = $prompt
    stream   = $false
    think    = $false
    options  = @{ num_predict = 512; temperature = 0.4; num_ctx = 8192 }
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 180
$response.response
