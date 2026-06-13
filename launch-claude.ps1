# launch-claude.ps1

# Set AgentRouter API base URL
$env:ANTHROPIC_BASE_URL = "https://agentrouter.org/"

# Set your AgentRouter API credentials
$env:ANTHROPIC_AUTH_TOKEN = "Acaj0jkTwXimyyfyudTeYnYQQ/dBxg=="
$env:ANTHROPIC_API_KEY   = "sk-ws4nM8Gp5isq7X3YSIkPj1COPyLBG6huaiHOqReLCYqm19k9"
#$env:ANTHROPIC_MODEL = "claude-sonnet-4-6"
$env:ANTHROPIC_MODEL = "claude-opus-4-6"
# Optional: verify variables
Write-Host "ANTHROPIC_BASE_URL=$env:ANTHROPIC_BASE_URL"
Write-Host "ANTHROPIC_AUTH_TOKEN=$env:ANTHROPIC_AUTH_TOKEN"
Write-Host "ANTHROPIC_API_KEY=$env:ANTHROPIC_API_KEY"
Write-Host "ANTHROPIC_MODEL=$env:ANTHROPIC_MODEL"
Write-Host "AgentRouter credentials configured."

# Launch Claude Cod
claude