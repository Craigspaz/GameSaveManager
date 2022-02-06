Write-Output "Updating..."

pipenv install
pipenv install --dev
pipenv run pyinstaller --noconsole -F --icon=favicon.ico main.py

$appdata_path = [Environment]::GetFolderPath('ApplicationData')
$install_path = "$appdata_path\GameSaveManager"

New-Item -Path $appdata_path -Name "GameSaveManager" -ItemType "directory" -ErrorAction SilentlyContinue
Copy-Item ".\dist\main.exe" -destination $install_path
Copy-Item ".\app_save_path_definitions.json" -destination $install_path

Write-Output "Completed Install of Update"