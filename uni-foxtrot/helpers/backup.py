import fnmatch
import subprocess
from helpers.dbsqlite import sql
import os

# We are going to create a backup system where we store the requirements, the database schema, and the folder structure


def generate_database_structure(output_file="docs/database_structure.txt"):
    """
    Generates a text file containing the database structure.
    """
    # Ensure the 'docs' directory exists
    if not os.path.exists("docs"):
        os.makedirs("docs")

    with open(output_file, "w") as f:
        f.write("=== INKY DATABASE STRUCTURE ===\n\n")

        # Get all tables
        tables = sql("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", [])

        for table in tables:
            # print(f"Processing table: {table['name']}")
            table_name = table['name']
            
            if table_name.startswith('sqlite_') or table_name == 'sqlean_':
                # print(f"Skipping system table: {table_name}")
                continue
            
            f.write(f"TABLE: {table_name}\n")
            f.write("-" * 40 + "\n")

            # Get table info (columns, types, etc.)
            columns = sql(f"PRAGMA table_info({table_name})", [])
            
            # print(f"Columns in {table_name}: {columns}")

            for col in columns:
                # print(f"Column details: {col}")
                cid = col['cid']
                name = col['name']
                type = col['type']
                notnull = col['notnull']
                dflt_value = col['dflt_value']
                pk = col['pk']

                # Rebuild column description
                desc_parts = []
                if type:
                    desc_parts.append(type)
                if notnull:
                    desc_parts.append("NOT NULL")
                    
                if pk:
                    desc_parts.append("PRIMARY KEY")
                    
                if dflt_value is not None:
                    desc_parts.append(f"DEFAULT {dflt_value}")
                else:
                    desc_parts.append("DEFAULT NULL")

                # Write column details to file
                f.write(f"  {cid:<3} {name:<20} {' '.join(desc_parts)}\n")

            # Get foreign keys if any
            foreign_keys = sql(f"PRAGMA foreign_key_list({table_name})", [])
            if foreign_keys:
                f.write("\n  Foreign Keys:\n")
                for fk in foreign_keys:
                   f.write(f"    {fk['from']} -> {fk['table']}.{fk['to']}\n")

            f.write("\n")

    print(f"Database structure written to {output_file}")


def generate_folder_structure():
    """Generate filtered folder structure and save to docs/folder_structure.txt"""
    try:
        exclude_folders = ['env_*', '.vscode', '*/__pycache__', 'node_modules', '*/.git']
        reduced_folders = ['bootstrap-5.3.2', 'bootswatch-5', 'fontawesome-pro-5.15.4', 'jquery-ui-1.14.1', 'mini-upload-form', 'uploads']

        output_lines = []

        for root, dirs, files in os.walk('.'):
            
            skip_folder = any(fnmatch.fnmatch(os.path.relpath(root, '.'), pat) for pat in exclude_folders)
            print(skip_folder, root)
            if skip_folder:
                continue
            
            # Calculate depth for indentation
            level = root.replace('.', '').count(os.sep)
            indent = '    ' * level

            # Add folder name
            folder_name = os.path.basename(root) or '.'
            output_lines.append(f"{indent}{folder_name}/")

            # Handle subdirectories - check for exclusions
            sub_indent = '    ' * (level + 1)
            dirs_to_remove = []

            for d in dirs:
                full_path = os.path.join(root, d)
                rel_path = os.path.relpath(full_path, '.')

                if any(exclude in rel_path for exclude in reduced_folders):
                    output_lines.append(f"{sub_indent}{d}/")
                    output_lines.append(f"{sub_indent}    ...")
                    dirs_to_remove.append(d)
                if any(fnmatch.fnmatch(rel_path, exclude) for exclude in exclude_folders):
                    dirs_to_remove.append(d)

            # Remove excluded directories from traversal
            for d in dirs_to_remove:
                dirs.remove(d)

            # Add files
            for file in files:
                output_lines.append(f"{sub_indent}{file}")

        with open('docs/folder_structure.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))

        print("Folder structure written to docs/folder_structure.txt")

    except Exception as e:
        print(f"Error generating folder structure: {e}")


def generate_pipfreeze_output():

    # The output will be in `docs/requirements.txt`
    try:
        output_lines = subprocess.check_output(['py', '-m', 'pip', 'freeze']).decode().strip().split('\n')

        with open('docs/requirements.txt', 'w', encoding='utf-8') as f:
            f.write(''.join(output_lines))

        print("Pip freeze output written to docs/requirements.txt")

    except Exception as e:
        print(f"Error generating pip freeze output: {e}")



if __name__ == "__main__":
    # Generate the database structure
    generate_database_structure()

    # Generate the pip freeze output
    generate_pipfreeze_output()
    
    # Generate the folder structure
    generate_folder_structure()
