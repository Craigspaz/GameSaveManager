# Game Save Manager

## Supported Operating Systems
Currently only Windows is supported

## Supported game launchers/stores
Currently only Steam is supported

## How does it work
1. This application runs on a cron. There is a sample installation script which shows how you can configure the cron.
1. The application will scan through the Steam configuration files on your system and find your games
1. The application will then check in the app_save_path_definitions.json file for a definition on where the game saves should be located
1. If that path exists it will make a copy of the backup based on the backup configuration

## Configuration file
A sample configuration file is provided to show you an example of how to configure backups

Below is the sample-config.json file provided with the code. The code looks for a file called config.json at run time.
```
{
    "steam_install_path": "C:\\Program Files (x86)\\Steam",
    "last_scan_time": "01/15/2022 20:41:53",
    "backup_methods": [
        {
            "backup_type": "FILE_SYSTEM",
            "backup_folder_path": "G:\\GameSaveBackups",
            "storage_format": "POINT_IN_TIME"
        },
        {
            "backup_type": "S3",
            "backup_bucket_name": "your bucket name here",
            "folder_prefix": "GameSaveManager",
            "storage_format": "OVERWRITE"
        }
    ]
}
```
steam_install_path is the path where Steam itself is installed.
last_scan_time is the last time a scan was run by this application
backup_methods is an array of backup methods you want to use

In the example above the first backup method is FILE_SYSTEM backup which means it will backup the files to a place on your filesystem. The path is specified in the value backup_folder_path.
the storage_format of POINT_IN_TIME means that it will create a separate folder for each backup. Note: This is the only supported backup format for FILE_SYSTEM.

The second backup method in the example above has a type of S3 which means it will use AWS S3 for the storage. Your credentials will need to be stored in the default profile in the .aws/credentials file. The IAM credentials in that folder will need to be able to read/write to the bucket specified in backup_bucket_name. It is recommended you have versioning enabled on this bucket. You can then specify a folder prefix. It is using a storage_format of OVERWRITE. This means it will write over existing files in S3. This is the only currently supported backup format for S3. If you have versioning enabled this will prevent data loss.

If you want to compile the code in this repo you can use pyinstaller
```
pyinstaller --noconsole -F --icon=favicon.ico main.py
```
Note: If you want to have a console window appear you can remove the --noconsole flag. It is recommended to not have the console appear for production use otherwise it might interrupt you while gaming.

## Dependencies
The repo uses pipenv.
- boto3
- pytz

## How to install

From Source: 
1. Clone this repo
1. pipenv install
1. pipenv install --dev
1. Rename sample-config.json to config.json
1. Edit config.json to the desired settings
1. pipenv run pyinstaller --noconsole -F --icon=favicon.ico main.py
1. Create a directory in %appdata%/GameSaveManager
1. Copy main.exe from the dist directory along with config.json and app_save_path_definitions.json to the directory you just created
1. Add a scheduled task in Windows to run on a schedule the way you would like it to run

With Install Script In Source:
1. Clone this repo
1. Edit sample-config.json to be the configuration file you want
1. Run install.ps1 (It will copy the files to %appdata%/GameSaveManager and it will add a scheduled task to task scheduler)


## How to update definitions

From Source:
1. Clone this repo
1. pipenv install
1. pipenv install --dev
1. pipenv run pyinstaller --noconsole -F --icon=favicon.ico main.py
1. Copy main.exe from the dist directory along with app_save_path_definitions.json to the folder located here: %appdata%/GameSaveManager

With the Upgrade Script In Source:
1. Clone this repo
1. Run update.ps1 (Note: If you the code is running you might get an error)