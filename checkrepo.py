import os
import shutil
import os
import json
import time
import ssl
import http.client
import sys

apikey=""

def get_all_files(repo_path):
    file_list = []
    for root, dirs, files in os.walk(repo_path):
        if '.git' in dirs:
            dirs.remove('.git')  # skip .git directory
        for file in files:
            full_path = os.path.join(root, file)
            file_list.append(full_path)
    return file_list


# Load API key
def load_api_key():
    try:
        with open('apikey.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("apikey.txt not found.")
        exit(1)

# Send prompt to OpenAI
def send_to_openai(prompt, model="gpt-4"):



    conn = http.client.HTTPSConnection("api.openai.com", context=ssl.create_default_context())
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {apikey}'
    }


    system= f"""

    It is assumed the following file has been tampered with. Find anything that may be suspcious or indicate tampering

    Generate a risk report it should contain

    - ALERT (if you think the file has been tampered with)
    - A Risk score 0-10
    - A short description of what you think the code is supposed to be doing
    - A list of things that are suspicious
    - A comment, if necessary

    Your output will be saved a txt file. So make sure to keep to the format
"""


    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1000
    })

    try:
        conn.request("POST", "/v1/chat/completions", body, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()

        if response.status != 200:
            print(f"OpenAI API error: {response.status} {response.reason}")
            return f"ERROR: {data.decode()}"

        result = json.loads(data)
        return result['choices'][0]['message']['content']
    except Exception as e:
        return f"Failed to contact OpenAI: {e}"


def create_risk_report(file_path):
    print(f"Currently processing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    filename = os.path.basename(file_path)
    dir_path = os.path.dirname(file_path)

    # Generate prompt
    prompt=f"""
    Filename: {filename}

    Code:
    -------------------
    {code}
    -------------------
    """


    airesponse=send_to_openai(prompt)

    # Save the risk report
    report_filename = f"RISKREPORT_{filename}.txt"
    report_path = os.path.join(dir_path, report_filename)
    try:
        with open(report_path, 'w', encoding='utf-8') as report_file:
            report_file.write(airesponse)  # In real use, you’d replace this with actual AI output
    except Exception as e:
        print(f"Failed to write risk report for {file_path}: {e}")
        return

    # Rename the original file to mark it as processed
    new_file_path = os.path.join(dir_path, "PROCESSED_"+filename )
    try:
        os.rename(file_path, new_file_path)
    except Exception as e:
        print(f"Failed to rename {file_path}: {e}")

def main():
    global apikey

    apikey=load_api_key()

    repo_path = input("Enter the path to the repository to check: ").strip()
    if not os.path.isdir(repo_path):
        print("Invalid path.")
        return




    os.chdir(repo_path)
    all_files = get_all_files(repo_path)

    if os.path.exists("repo_clean_mark"):
        print("This repo has already been processed.")
        sys.exit()






    remaining=len(all_files)

    for file_path in all_files:
        create_risk_report(file_path)
        remaining-=1
        print(str(remaining)+" files left")

    # Create the file and write "complete" into it
    with open("repo_clean_mark", "w") as f:
        f.write("complete")

    print("Done.")

if __name__ == "__main__":
    main()

