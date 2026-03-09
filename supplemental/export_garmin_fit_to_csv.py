import os
from fitparse import FitFile
import pandas as pd

directory = "."

rows = []

# loop through subdirectories
for subdir in os.listdir(directory):
    subdir_path = os.path.join(directory, subdir)

    if os.path.isdir(subdir_path):
        for file in os.listdir(subdir_path):
            if file.endswith(".fit") and "wellness" in file.lower():
                filepath = os.path.join(subdir_path, file)

                fitfile = FitFile(filepath)

                for record in fitfile.get_messages("monitoring"):
                    data = {}

                    for field in record:
                        data[field.name] = field.value

                    data["source_file"] = file
                    data["source_folder"] = subdir

                    rows.append(data)

df = pd.DataFrame(rows)

output_csv = os.path.join(directory, "combined_monitoring.csv")
df.to_csv(output_csv, index=False)
