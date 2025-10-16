Get-ChildItem -Path "m:\CALife\CAShop - 구매대행\_code" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

Get-ChildItem -Path "m:\CALife\CAShop - 구매대행\_code" -Recurse -Directory -Filter "__pycache__" | Select-Object FullName