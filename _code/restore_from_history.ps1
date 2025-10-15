# VS Code History에서 cfg_utils와 image_utils 파일 복구 스크립트

$historyPath = "$env:APPDATA\Code\User\History"
$targetModules = @("cfg_utils", "image_utils")

Write-Host "=== VS Code History 파일 복구 스크립트 ===" -ForegroundColor Cyan
Write-Host ""

# 복구할 파일 목록 수집
$filesToRestore = @()

Get-ChildItem $historyPath -Recurse -Filter "entries.json" | ForEach-Object {
    $entriesFile = $_
    $json = Get-Content $_.FullName | ConvertFrom-Json
    
    # cfg_utils 또는 image_utils 관련 파일만 필터링
    if ($json.resource -match ($targetModules -join "|")) {
        # 가장 최근 .py 파일 찾기
        $latestPy = Get-ChildItem $entriesFile.DirectoryName -Filter "*.py" -ErrorAction SilentlyContinue | 
                    Sort-Object LastWriteTime -Descending | 
                    Select-Object -First 1
        
        if ($latestPy) {
            # URL 디코딩
            $originalPath = [System.Uri]::UnescapeDataString($json.resource)
            $originalPath = $originalPath -replace "^file:///", ""
            $originalPath = $originalPath -replace "/", "\"
            
            $filesToRestore += [PSCustomObject]@{
                OriginalPath = $originalPath
                HistoryPath  = $latestPy.FullName
                LastModified = $latestPy.LastWriteTime
            }
        }
    }
}

# 최근 수정 순으로 정렬
$filesToRestore = $filesToRestore | Sort-Object LastModified -Descending

Write-Host "발견된 파일: $($filesToRestore.Count)개" -ForegroundColor Yellow
Write-Host ""

# 파일 목록 표시
$filesToRestore | Format-Table -Property @{
    Label="원본 파일"
    Expression={ $_.OriginalPath.Substring($_.OriginalPath.LastIndexOf("modules\")) }
    Width=60
}, @{
    Label="마지막 수정"
    Expression={ $_.LastModified.ToString("yyyy-MM-dd HH:mm:ss") }
    Width=20
} -AutoSize

Write-Host ""
$confirm = Read-Host "이 파일들을 복구하시겠습니까? (Y/N)"

if ($confirm -eq "Y" -or $confirm -eq "y") {
    $restored = 0
    $failed = 0
    
    foreach ($file in $filesToRestore) {
        try {
            # 디렉터리 생성
            $dir = Split-Path $file.OriginalPath -Parent
            if (!(Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
            }
            
            # 파일 복사
            Copy-Item -Path $file.HistoryPath -Destination $file.OriginalPath -Force
            Write-Host "[OK] $($file.OriginalPath.Substring($file.OriginalPath.LastIndexOf("modules\")))" -ForegroundColor Green
            $restored++
        }
        catch {
            Write-Host "[FAIL] $($file.OriginalPath.Substring($file.OriginalPath.LastIndexOf("modules\"))) - $($_.Exception.Message)" -ForegroundColor Red
            $failed++
        }
    }
    
    Write-Host ""
    Write-Host "=== 복구 완료 ===" -ForegroundColor Cyan
    Write-Host "성공: $restored 개" -ForegroundColor Green
    Write-Host "실패: $failed 개" -ForegroundColor Red
}
else {
    Write-Host "복구 취소됨" -ForegroundColor Yellow
}
