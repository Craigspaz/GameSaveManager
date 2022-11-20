import json
import datetime
import os
import shutil
import boto3
import winreg

print("Starting up Version: v1.0.2.0")

# TODO: Pull Value dynamically
OPERATING_SYSTEM = 0 # 0 is Windows, 1 is Linux and 2 is Mac OS

default_steam_path = "C:/Program Files (x86)/Steam"
time_scan_started = datetime.datetime.now()
APPDATA =  os.getenv('APPDATA')
LOCALAPPDATA =  os.getenv("LOCALAPPDATA")
USERPROFILE =  os.getenv("USERPROFILE")
PROGRAMDATA = os.getenv("PROGRAMDATA")
PUBLIC = os.getenv("PUBLIC")

'''
    Gets the file system paths to where the steam games are installed. This will be a list. For example, you could have an install directory in the default directory and on an external disk.
'''
def get_library_paths(steam_path):
    print("Get Library Paths")

    paths = []

    current_path = {"path": "", "apps": []}
    libraryFilePath = None
    try:
        libraryFilePath = open(steam_path + "\\steamapps\\libraryfolders.vdf", "r")
    except:
        print("Failed to open libraryfolders.vdf in the steam install/steamapps directory. Make sure your steam install path is correct")
        exit(-1)

    in_apps = False
    for line in libraryFilePath:
        if line.strip().startswith("\"path\""):
            current_path["path"] = line.strip().split("\"")[3]

        if line.strip().startswith("\"apps\""):
            in_apps = True
            continue

        if in_apps:
            if line.strip().startswith("{"):
                continue
            if line.strip().startswith("}"):
                in_apps = False
                paths.append(current_path)
                current_path = {"path": "", "apps": []}
                continue
            app_id = line.strip().split("\"")[1]
            current_path["apps"].append(app_id)

    libraryFilePath.close()
    return paths

'''
    Reads the config.json file from the disk
'''
def read_config_file():
    config_file_contents = ""
    config_file = open("config.json", "r")
    config_file_contents = config_file.read()
    config_file.close()
    try:
        parsed_config_file = json.loads(config_file_contents)
        return parsed_config_file
    except:
        print("Config file was not in a valid json format")
        exit(-2)

'''
    Reads the save game definitions file from the disk
'''
def get_save_path_definitions():
    definitions_raw = ""
    definitions_file = None
    try:
        definitions_file = open("app_save_path_definitions.json", "r")
    except:
        print("Failed to open save game definitions file")
        exit(-3)
    definitions_raw = definitions_file.read()
    definitions_file.close()
    return json.loads(definitions_raw)

'''
    Returns True if the directory needs to be backed up else it returns False.
'''
def does_dir_need_to_be_backuped(dir, last_scan_time, filter=None):
    print("Last Scan Time: " + str(last_scan_time.strftime("%Y_%m_%d__%H_%M_%S_%f")))
    files = get_list_of_directory_files(dir, filter)
    for file in files:
        try:
            modified_time = os.path.getmtime(file)
            modified_date_time = datetime.datetime.fromtimestamp(modified_time)
            if modified_date_time > last_scan_time:
                return True
        except:
            print("File no longer exits. Skipping...")
    print("Dir does not need to be backed up")
    return False

'''
    Returns True if the file needs to be backed up else it returns False
'''
def does_file_need_to_be_backuped(file, last_scan_time):
    modified_time = os.path.getmtime(file)
    modified_date_time = datetime.datetime.fromtimestamp(modified_time)
    if modified_date_time > last_scan_time:
        return True
    return False

'''
    Returns a list of files in a folder going down recursively. 
    If a filter is provided it will check to see if the filename ends with that filter. The filter is mostly meant for file extension filtering
'''
def get_list_of_directory_files(dir, filter=None):
    files = []
    for item in os.scandir(dir):
        if item.is_file():
            if filter != None:
                print("Filter is not none. Checking if file '" + str(item.path) + "' ends with filter: " + str(filter))
                if item.path.lower().endswith(filter.lower()):
                    print("It does")
                    files.append(item.path.replace("\\", "/"))
            else:
                files.append(item.path)
        elif item.is_dir():
            tmp = get_list_of_directory_files(item.path, filter)
            for i in tmp:
                files.append(i)
    return files

'''
    Returns a file path to the folder/file that needs to be backed up.
'''
def resolve_path(path, app=None, library_path=None, steam_install_path=""):
    tmp = path.replace("|STEAMINSTALLDIR|", steam_install_path)
    tmp = tmp.replace("%APPDATA%", APPDATA)
    tmp = tmp.replace("%USERPROFILE%", USERPROFILE)
    tmp = tmp.replace("%LOCALAPPDATA%", LOCALAPPDATA)
    tmp = tmp.replace("%PROGRAMDATA%", PROGRAMDATA)
    tmp = tmp.replace("%PUBLIC%", PUBLIC)
    if app != None and library_path != None and app != "USERDATA":
        app_folder_name = None
        # Get appmanifest
        try:
            manifest_file = open(str(library_path["path"]) + "/steamapps/appmanifest_" + str(app) + ".acf", "r")
            for line in manifest_file:
                if line.strip().startswith("\"installdir\""):
                    app_folder_name = line.strip().split("\"")[3]
            manifest_file.close()
        except:
            print("Failed to open/read manifest file. Skipping app: " + str(app))
        if app_folder_name != None:
            print("app_folder_name: " + str(app_folder_name))
            tmp = tmp.replace("|PATHTOGAME|", str(library_path["path"]) + "/steamapps/common/" + str(app_folder_name).strip())
        else:
            print("App Folder is None")
    if OPERATING_SYSTEM == 0:
        tmp = tmp.replace("\\", "/")
    return tmp

'''
    Creates a directory if it does not exist in path
'''
def create_dir_if_needed(base_path, relative_path):
    folders = relative_path.split("/")
    folders = folders[0:len(folders) - 1]
    print("Base Path: " + str(base_path) + "  Relative Path: " + str(relative_path))

    if os.path.isdir(base_path) == False:
        os.mkdir(base_path)

    current_path = ""
    for folder in folders:
        path = base_path + current_path + folder
        print("Checking if path exists: " + str(path))
        if os.path.isdir(path) == False:
            print("Path does not so creating it")
            os.mkdir(path)
        current_path += folder + "/"

'''
    Returns Windows Registry keys
'''
def get_keys(registry_backup, registry_key_handle, parent_key_path):
    counter = 0
    while True:
        try:
            key_name = winreg.EnumKey(registry_key_handle, counter)
            registry_backup.append({"Key": parent_key_path + "\\" + key_name, "Values": []})
            
            sub_key = winreg.OpenKey(registry_key_handle, key_name)
            counter1 = 0
            while True:
                try:
                    value = winreg.EnumValue(sub_key, counter1)
                    parsed_value = {"Name": value[0], "Value": value[1], "Type": value[2]}
                    # print(value)
                    registry_backup[-1]["Values"].append(parsed_value)
                    counter1 += 1
                except:
                    break
            registry_backup = get_keys(registry_backup, sub_key, parent_key_path + "\\" + key_name)
            counter += 1
        except:
            break
    return registry_backup

'''
    Returns True if the save path is defined as a value that we can skip
    NA means there are no save games/files that need to be backed up
    TBD means we don't yet know if there are files to be backed up
    IN_USER_DATA means the files are stored in the Steam User Data folder which we back up at a separate point so we don't need to back this up again
'''
def can_skip_backup(save_path_definitions, app):
    if ("folder" in save_path_definitions[app] and save_path_definitions[app]["folder"] == "|NA|") or ("filter" in save_path_definitions[app] and save_path_definitions[app]["filter"] == "|NA|"):
        print("App '" + str(app) + "' does not have saves or no save location is known")
        return True
    elif ("folder" in save_path_definitions[app] and save_path_definitions[app]["folder"] == "|TBD|") or ("filter" in save_path_definitions[app] and save_path_definitions[app]["filter"] == "|TBD|"):
        print("App '" + str(app) + "' has an unknown save location")
        return True
    elif ("folder" in save_path_definitions[app] and save_path_definitions[app]["folder"] == "|IN_USER_DATA|") or ("filter" in save_path_definitions[app] and save_path_definitions[app]["filter"] == "|IN_USER_DATA|"):
        print("App '" + str(app) + "' has its saves stored in the Steam User Data which is automatically backed up")
        return True
    elif "file" in save_path_definitions[app] and save_path_definitions[app]["file"] == "|NA|":
        print("App '" + str(app) + "' does not have saves or no save location is known")
        return True
    elif "file" in save_path_definitions[app] and save_path_definitions[app]["file"] == "|TBD|":
        print("App '" + str(app) + "' has an unknown save location")
        return True
    elif "file" in save_path_definitions[app] and save_path_definitions[app]["file"] == "|IN_USER_DATA|":
        print("App '" + str(app) + "' has its saves stored in the Steam User Data which is automatically backed up")
        return True
    elif "folders" in save_path_definitions[app] and len(save_path_definitions[app]["folders"]) == 0:
        print("App '" + str(app) + "' has no folders to backup")
        return True
    return False

'''
    Copies backup of file to File System
'''
def backup_method_filesystem(backup_method, app, file_name):
    backup_folder_base_path = None
    storage_format = None
    if "backup_folder_path" in backup_method:
        backup_folder_base_path = backup_method["backup_folder_path"]
    if "storage_format" in backup_method:
        storage_format = backup_method["storage_format"]
    if backup_folder_base_path == None:
        print("Backup Method is a FILE SYSTEM Type but does not have a path to store the backups")
        return
    if storage_format == None or storage_format == "POINT_IN_TIME":
        print("Storage Format is using DEFAULT POINT_IN_TIME")
        if os.path.isdir(backup_folder_base_path + "/" + str(app) + "/") == False:
            os.mkdir(backup_folder_base_path + "/" + str(app) + "/")
        folder_path = backup_folder_base_path + "/" + str(app) + "/" + str(datetime.datetime.now().strftime("%Y_%m_%d__%H_%M_%S_%f") + "/")
        print("Creating Backup folder: " + str(folder_path))
        if OPERATING_SYSTEM == 0:
            folder_path = folder_path.replace("\\", "/")
        source_file = file_name.replace("\\", "/")
        source_filename_split = source_file.split("/")
        source_file_name = source_filename_split[len(source_filename_split) - 1]
        
        destination = folder_path + source_file_name
        if OPERATING_SYSTEM == 0:
            destination = destination.replace("\\", "/")
        print("Copying file: " + str(source_file) + " to: " + str(destination))
        create_dir_if_needed(folder_path, source_file_name)
        shutil.copy(source_file, destination)

'''
    Copies backup of file to S3
'''
def backup_method_s3(backup_method, app, file_name, s3_resource, s3_client, save_path=None):
    print("S3 Backup: File Name: " + str(file_name))
    backup_bucket_name = None
    folder_prefix = None
    storage_format = None
    if "backup_bucket_name" in backup_method:
        backup_bucket_name = backup_method["backup_bucket_name"]
    if "folder_prefix" in backup_method:
        folder_prefix = backup_method["folder_prefix"]
    if "storage_format" in backup_method:
        storage_format = backup_method["storage_format"]
    if (storage_format == None or storage_format == "OVERWRITE") and s3_resource != None:
        print("Storage Format is using DEFAULT POINT_IN_TIME")
        source_file = file_name.replace("\\", "/")
        source_filename_split = source_file.split("/")
        source_file_name = source_filename_split[len(source_filename_split) - 1]
        
        if save_path == None:
            if folder_prefix != None:
                save_path = str(folder_prefix + "/" + str(app) + "/" + str(source_file_name)).replace("\\", "/")
            else:
                save_path = str(str(app) + "/" + str(source_file_name)).replace("\\", "/")

        print("File Name S3: " + str(save_path))

        response = None
        try:
            response = s3_client.head_object(Bucket=backup_bucket_name, Key=save_path)
        except:
            print("File is not in S3. Uploading...")
        print(response)
        local_file_datetime = None
        try:
            local_file_time = os.path.getmtime(source_file)
            local_file_datetime = datetime.datetime.fromtimestamp(local_file_time, tz=datetime.timezone.utc)
        except Exception as e:
            print("Source file likely no longer exists: " + str(e))
            return

        if response != None and "Metadata" in response:
            metadata = response["Metadata"]
            if "modified_date" in metadata:
                remote_modified_date = datetime.datetime.strptime(response["Metadata"]["modified_date"], "%Y_%m_%d__%H_%M_%S_%f")
                print("Remote Modified Date: " + str(remote_modified_date.strftime("%Y_%m_%d__%H_%M_%S_%f")) + " | Local File Time: " + str(local_file_datetime.strftime("%Y_%m_%d__%H_%M_%S_%f")))
                if str(remote_modified_date.strftime("%Y_%m_%d__%H_%M_%S_%f")) == str(local_file_datetime.strftime("%Y_%m_%d__%H_%M_%S_%f")):
                    print("Modified dates are the same so skipping...")
                    return
        try:
            if local_file_datetime != None:
                s3_resource.meta.client.upload_file(source_file, backup_bucket_name, save_path, ExtraArgs={"Metadata": {"modified_date": str(local_file_datetime.strftime("%Y_%m_%d__%H_%M_%S_%f"))}})
            else:
                print("Strangely file does not have a modified datetime...")
        except Exception as e:
            print("S3 Upload failed: " + str(e))

'''
    Backup Windows Registry keys for a specific game
'''
def backup_registry_save(save_path_definitions, app, user_defined_config, s3_client, s3_resource):
    registry_key = save_path_definitions[app]["registry"]
    stripped_registry_key = None
    key_handle = winreg.HKEY_CURRENT_USER
    if "HKEY_LOCAL_MACHINE" in registry_key:
        key_handle = winreg.HKEY_LOCAL_MACHINE
        stripped_registry_key = registry_key.replace("HKEY_LOCAL_MACHINE\\", "")
    else:
        stripped_registry_key = registry_key.replace("HKEY_CURRENT_USER\\", "")

    windows_registry_handle = winreg.ConnectRegistry(None, key_handle)
    registry_key_handle = winreg.OpenKey(windows_registry_handle, stripped_registry_key)
    registry_backup = [{"Key": registry_key, "Values": []}]

    counter1 = 0
    while True:
        try:
            value = winreg.EnumValue(registry_key_handle, counter1)
            parsed_value = {"Name": value[0], "Value": value[1], "Type": value[2]}
            registry_backup[0]["Values"].append(parsed_value)
            counter1 += 1
        except:
            break

    registry_backup = get_keys(registry_backup, registry_key_handle, registry_key)
    print("Registry Backup: " + str(registry_backup))
    if registry_backup != None:

        tmp_file = open("./tmp_file.json", "w")
        try:
            tmp_file.write(json.dumps(registry_backup))
        except:
            tmp_file.write(str(registry_backup))
        tmp_file.close()

        if "backup_methods" in user_defined_config:
            for backup_method in user_defined_config["backup_methods"]:
                if "backup_type" in backup_method and backup_method["backup_type"] == "FILE_SYSTEM":
                    backup_method_filesystem(backup_method, app, "./tmp_file.json")
                elif "backup_type" in backup_method and backup_method["backup_type"] == "S3":
                    backup_method_s3(backup_method, app, "./tmp_file.json", s3_resource, s3_client)

        os.remove("./tmp_file.json")

'''
    Backs up a file
'''
def backup_file(save_path_definitions, app, path, steam_path, user_defined_config, last_scan_time, s3_resource, s3_client):
    raw_save_game_location = str(save_path_definitions[app]["file"])
    print("RAW Save Game Location: " + str(raw_save_game_location))
    processed_path = resolve_path(raw_save_game_location, app, path, steam_path)
    print("Processed Path: " + processed_path)

    if os.path.isfile(processed_path):
        print("App '" + str(app) + "' Save Location EXISTS")
        if does_file_need_to_be_backuped(processed_path, last_scan_time) == False:
            print("Path does not need to be backup. Skipping...")
            return

        if "backup_methods" in user_defined_config:
            for backup_method in user_defined_config["backup_methods"]:
                if "backup_type" in backup_method and backup_method["backup_type"] == "FILE_SYSTEM":
                    backup_method_filesystem(backup_method, app, processed_path)
                elif "backup_type" in backup_method and backup_method["backup_type"] == "S3":
                    backup_method_s3(backup_method, app, processed_path, s3_resource, s3_client)


'''
    Backup Folder to File System
'''
def backup_folder_file_system(backup_method, app, processed_path, friendly_name=None, filter=None):
    backup_folder_base_path = None
    storage_format = None
    if "backup_folder_path" in backup_method:
        backup_folder_base_path = backup_method["backup_folder_path"]
    if "storage_format" in backup_method:
        storage_format = backup_method["storage_format"]
    if backup_folder_base_path == None:
        print("Backup Method is a FILE SYSTEM Type but does not have a path to store the backups")
        return
    if storage_format == None or storage_format == "POINT_IN_TIME":
        print("Storage Format is using DEFAULT POINT_IN_TIME")
        if os.path.isdir(backup_folder_base_path + "/" + str(app) + "/") == False:
            os.mkdir(backup_folder_base_path + "/" + str(app) + "/")
        folder_path = backup_folder_base_path + "/" + str(app) + "/" + str(datetime.datetime.now().strftime("%Y_%m_%d__%H_%M_%S_%f")) + "/"
        if friendly_name != None:
            folder_path += str(friendly_name) + "/"
        print("Creating Backup folder: " + str(folder_path))
        if OPERATING_SYSTEM == 0:
            folder_path = folder_path.replace("\\", "/")
        if filter == None:
            shutil.copytree(processed_path, folder_path)
        else:
            files_to_copy = get_list_of_directory_files(processed_path, filter.replace("*",""))
            for file in files_to_copy:
                source_file = file.replace("\\", "/")
                relative_path = source_file.replace(processed_path.replace("\\", "/") + "/", "")
                create_dir_if_needed(folder_path, relative_path)
                destination = source_file.replace(processed_path.replace("\\", "/") + "/", folder_path)
                if OPERATING_SYSTEM == 0:
                    destination = destination.replace("\\", "/")
                print("Copying file: " + str(source_file) + " to: " + str(destination))
                try:
                    shutil.copy(source_file, destination)
                except Exception as e:
                    print("Failed to copy file. This can happen if the source file was deleted: " + str(e))
    else:
        print("Unsupported storage format selected...")

'''
    Backs up a single folder
'''
def backup_folder(processed_path, app, last_scan_time, user_defined_config, friendly_name, s3_resource, s3_client):
    # Check if the path exists
    if os.path.isdir(processed_path):
        print("App '" + str(app) + "' Save Location EXISTS")
        if does_dir_need_to_be_backuped(processed_path, last_scan_time) == False:
            print("Path does not need to be backup. Skipping...")
            return
        else:
            print("Path needs to be backup...")
        if "backup_methods" in user_defined_config:
            for backup_method in user_defined_config["backup_methods"]:
                if "backup_type" in backup_method and backup_method["backup_type"] == "FILE_SYSTEM":
                    backup_folder_file_system(backup_method, app, processed_path, friendly_name)
                elif "backup_type" in backup_method and backup_method["backup_type"] == "S3":
                    folder_prefix = None
                    storage_format = None
                    if "folder_prefix" in backup_method:
                        folder_prefix = backup_method["folder_prefix"]
                    if "storage_format" in backup_method:
                        storage_format = backup_method["storage_format"]
                    if (storage_format == None or storage_format == "OVERWRITE") and s3_resource != None:
                        print("Storage Format is using DEFAULT POINT_IN_TIME")
                        files = get_list_of_directory_files(processed_path)
                        for file in files:
                            save_path = None
                            if folder_prefix != None:
                                save_path = str(folder_prefix + "/" + str(app) + "/" + str(friendly_name) + str(file.replace(processed_path, ""))).replace("\\", "/")
                            else:
                                save_path = str(str(app) + "/" + str(friendly_name) + str(file.replace(processed_path, ""))).replace("\\", "/")
                            backup_method_s3(backup_method, app, file, s3_resource, s3_client, save_path)
                    else:
                        if storage_format != "OVERWRITE":
                            print("Storage format is not overwrite. Overwrite is currently the only supported method")
    else:
        print("App '" + str(app) + "' Save Location does not exist")

'''
    Backup multiple folders Folders
'''
def backup_folders(save_path_definitions, app, path, steam_path, last_scan_time, user_defined_config, s3_resource, s3_client):
    raw_save_game_location = None
    for folder in save_path_definitions[app]["folders"]:
        raw_save_game_location = str(folder["Path"])
        friendly_name = str(folder["FriendlyName"])
        print("RAW Save Game Location: " + str(raw_save_game_location))
        processed_path = resolve_path(raw_save_game_location, app, path, steam_path)
        print("Processed Path: " + str(processed_path))
        backup_folder(processed_path, app, last_scan_time, user_defined_config, friendly_name, s3_resource, s3_client)

def main():
    user_defined_config = read_config_file()
    last_scan_time = None
    if "last_scan_time" in user_defined_config:
        print("Found last scan time")
        last_scan_time = datetime.datetime.strptime(user_defined_config["last_scan_time"], "%m/%d/%Y %H:%M:%S")
        print("Last Scan Time: " + str(user_defined_config["last_scan_time"]))
    s3_resource = None
    s3_client = None
    if "backup_methods" in user_defined_config:
        for backup_method in user_defined_config["backup_methods"]:
            if "backup_type" in backup_method and backup_method["backup_type"] == "S3":
                s3_resource = boto3.resource("s3")
                s3_client = boto3.client("s3")   

    steam_path = default_steam_path
    if "steam_install_path" in user_defined_config:
        steam_path = user_defined_config["steam_install_path"]

    library_paths = get_library_paths(steam_path)
    save_path_definitions = get_save_path_definitions()

    if len(library_paths) >= 1:
        library_paths[0]["apps"].append("USERDATA")
    for path in library_paths:
        print("Processing Path: " + str(path["path"]))
        for app in path["apps"]:
            print("Processing App: " + str(app))
            if app in save_path_definitions:
                print("Found app '" + str(app) + "' in definitions file")

                if "folder" in save_path_definitions[app] or "filter" in save_path_definitions[app]:
                    if "folder" in save_path_definitions[app]:
                        print("APP Save Type is FOLDER")
                    else:
                        print("APP Save Type is FILTER")

                    if can_skip_backup(save_path_definitions, app):
                        continue
                    
                    raw_save_game_location = None
                    filter = None
                    if "folder" in save_path_definitions[app]:
                        raw_save_game_location = str(save_path_definitions[app]["folder"])
                    elif "filter" in save_path_definitions[app]:
                        raw_save_game_location = str(save_path_definitions[app]["filter"])
                        print("RAW Filtered Save Game Location: " + str(raw_save_game_location))
                        items = raw_save_game_location.split("/")
                        filter = items[len(items) - 1]
                        raw_save_game_location = raw_save_game_location[0:raw_save_game_location.rfind("/")]
                    else:
                        print("Unexpected error occured!")

                    print("RAW Save Game Location: " + str(raw_save_game_location))
                    processed_path = resolve_path(raw_save_game_location, app, path, steam_path)
                    print("Processed Path: " + str(processed_path))
                    print("Filter: " + str(filter))

                    # Check if the path exists
                    test = os.path.isdir(processed_path)
                    if test:
                        print("App '" + str(app) + "' Save Location EXISTS")
                        if filter != None:
                            if does_dir_need_to_be_backuped(processed_path, last_scan_time, filter.replace("*", "")) == False:
                                print("Path does not need to be backup. Skipping...")
                                continue
                        else:
                            if does_dir_need_to_be_backuped(processed_path, last_scan_time) == False:
                                print("Path does not need to be backup. Skipping...")
                                continue
                            else:
                                print("Path needs to be backup...")
                        if "backup_methods" in user_defined_config:
                            for backup_method in user_defined_config["backup_methods"]:
                                if "backup_type" in backup_method and backup_method["backup_type"] == "FILE_SYSTEM":
                                    backup_folder_file_system(backup_method, app, processed_path, None, filter)
                                elif "backup_type" in backup_method and backup_method["backup_type"] == "S3":
                                    folder_prefix = None
                                    storage_format = None
                                    if "folder_prefix" in backup_method:
                                        folder_prefix = backup_method["folder_prefix"]
                                    if "storage_format" in backup_method:
                                        storage_format = backup_method["storage_format"]
                                    if (storage_format == None or storage_format == "OVERWRITE") and s3_resource != None:
                                        print("Storage Format is using DEFAULT POINT_IN_TIME")
                                        # time_stamp = str(datetime.datetime.now().strftime("%Y_%m_%d__%H_%M_%S_%f"))
                                        files = None
                                        if filter != None:
                                            files = get_list_of_directory_files(processed_path, filter.replace("*", ""))
                                        else:
                                            files = get_list_of_directory_files(processed_path)
                                        for file in files:
                                            save_path = None
                                            if folder_prefix != None:
                                                save_path = str(folder_prefix + "/" + str(app) + str(file.replace(processed_path, ""))).replace("\\", "/")
                                            else:
                                                save_path = str(str(app) + str(file.replace(processed_path, ""))).replace("\\", "/")
                                            backup_method_s3(backup_method, app, file, s3_resource, s3_client, save_path)
                    else:
                        print("App '" + str(app) + "' Save Location does not exist")
                elif "folders" in save_path_definitions[app]:
                    if can_skip_backup(save_path_definitions, app):
                        continue
                    backup_folders(save_path_definitions, app, path, steam_path, last_scan_time, user_defined_config, s3_resource, s3_client)
                elif "file" in save_path_definitions[app]:
                    print("APP Save Type is FILE")
                    if can_skip_backup(save_path_definitions, app):
                        continue
                    backup_file(save_path_definitions, app, path, steam_path, user_defined_config, last_scan_time, s3_resource, s3_client)
                elif "registry" in save_path_definitions[app]:
                    print("APP Save Type is WINDOWS REGISTRY")
                    if OPERATING_SYSTEM == 0: # If OS is Windows
                        backup_registry_save(save_path_definitions, app, user_defined_config, s3_client, s3_resource)
                    else:
                        print("Only Windows devies have registry keys. If you are seeing this I suspect you are not running on Windows?")
            else:
                print("App '" + str(app) + "' is not in Save Path Definitions")
    user_defined_config["last_scan_time"] = time_scan_started.strftime("%m/%d/%Y %H:%M:%S")
    user_config_file = open("config.json", "w")
    user_config_file.write(json.dumps(user_defined_config))
    user_config_file.close()


if __name__ == "__main__":
    main()