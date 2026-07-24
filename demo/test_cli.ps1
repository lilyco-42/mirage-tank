# CLI Multi-Case Automation Test Script
$testCases = @(
    @{ hidden="src/1.jpg"; surface="src/1.jpg"; expected="B372158F69769F209E2C78143FCD563AB2AFE5FC5E637FE1EBB4B56C2034F427"; name="Case 1: Identical Images (JPG)" },
    @{ hidden="src/1.jpg"; surface="src/2.png"; expected="75C709E74EC80BD7E3D54FF40B56B863E627F36F316684AE148E6C8892B35684"; name="Case 2: JPG + PNG (Different Sizes)" },
    @{ hidden="src/2.png"; surface="src/3.png"; expected="C63950223A933009BA7E42B7E8208C570EA13D6887E071B0C866A9B8E7F91441"; name="Case 3: PNG + PNG" }
)

$testOutput = "test_run_output.png"
$allPassed = $true

Write-Host "Running CLI Multi-Case Suite..." -ForegroundColor Cyan

foreach ($case in $testCases) {
    Write-Host "`nTesting: $($case.name)" -ForegroundColor Yellow

    # Clean up
    if (Test-Path $testOutput) { Remove-Item $testOutput }

    # Run CLI
    cargo run --quiet --bin demo-cli -- $($case.hidden) $($case.surface) $testOutput

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Error: CLI crashed!" -ForegroundColor Red
        $allPassed = $false
        continue
    }

    # Calculate Hash
    $actualHash = (Get-FileHash $testOutput -Algorithm SHA256).Hash

    if ($actualHash -eq $case.expected) {
        Write-Host "  Result: PASSED" -ForegroundColor Green
    } else {
        Write-Host "  Result: FAILED" -ForegroundColor Red
        Write-Host "  Expected: $($case.expected)"
        Write-Host "  Actual:   $actualHash"
        $allPassed = $false
    }
}

if (Test-Path $testOutput) { Remove-Item $testOutput }

Write-Host "`n-------------------------------"
if ($allPassed) {
    Write-Host "ALL TESTS PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "SOME TESTS FAILED!" -ForegroundColor Red
    exit 1
}
