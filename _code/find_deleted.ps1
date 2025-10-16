# 6시간 이내 삭제된 modules 파일 검색 스크립트
$cutoffTime = (Get-Date).AddHours(-48)
$deleted = @()

Get-ChildItem "$env:APPDATA\Code\User\History" -Directory | ForEach-Object {
    $dir = $_
    $entries = Join-Path $dir.FullName "entries.json"
    if (Test-Path $entries) {
        try {
            $json = Get-Content $entries -Raw | ConvertFrom-Json
            if ($json.resource -match "docs/.*\.md") {
                $mdFiles = Get-ChildItem $dir.FullName -Filter "*.md" -ErrorAction SilentlyContinue | 
                          Where-Object { $_.LastWriteTime -gt $cutoffTime }
                
                if ($mdFiles) {
                    $path = [System.Uri]::UnescapeDataString($json.resource) -replace "^file:///", "" -replace "/", "\"
                    
                    if (!(Test-Path $path)) {
                        $deleted += "$($path -replace '.*\\docs\\', 'docs\') | $($mdFiles[0].LastWriteTime.ToString('HH:mm:ss')) | $($mdFiles[0].FullName)"
                    }
                }
            }
        } catch {}
    }
}

$deleted | Sort-Object | Out-File "m:\CALife\CAShop - 구매대행\_code\deleted_files_report.txt"
Write-Host "삭제된 파일: $($deleted.Count)개"
Write-Host "보고서 저장: deleted_files_report.txt"
