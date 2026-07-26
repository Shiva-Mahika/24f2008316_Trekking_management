# check.py

import checksumdir 

# Replace "folder_name" with the actual folder path
hash = checksumdir.dirhash(".")
print("Directory Checksum:", hash)