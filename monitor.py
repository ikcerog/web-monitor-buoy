import requests
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- Configuration ---
MONITORED_URLS = {
    "Google_Homepage": "https://www.google.com",
    "UWM Press Releases": "https://www.uwm.com/press-releases"
}
HASH_STORAGE_FILE = "url_hashes.json"
XML_OUTPUT_FILE = "monitoring_report.xml"

def check_for_changes():
    """Fetches URLs, calculates content hashes, compares them, and reports changes."""
    # 1. Load last known hashes
    last_hashes = {}
    if os.path.exists(HASH_STORAGE_FILE):
        try:
            with open(HASH_STORAGE_FILE, 'r') as f:
                last_hashes = json.load(f)
        except json.JSONDecodeError:
             print(f"Warning: Could not decode {HASH_STORAGE_FILE}. Starting fresh.")
    
    current_hashes = {}
    changes_detected = []

    for name, url in MONITORED_URLS.items():
        try:
            # 2. Fetch the content
            response = requests.get(url, timeout=15)
            response.raise_for_status() # Check for bad status codes
            
            # 3. Calculate the new hash
            content_hash = hashlib.md5(response.content).hexdigest()
            current_hashes[name] = content_hash
            
            # 4. Comparison and Reporting
            if name in last_hashes and last_hashes[name] != content_hash:
                print(f"🚨 Change detected on: {name}")
                changes_detected.append({
                    "name": name,
                    "url": url,
                    "timestamp": datetime.now().isoformat(),
                    "status": "Content Changed",
                    "hash_change": f"Old: {last_hashes[name][:8]}... -> New: {content_hash[:8]}..."
                })
            elif name not in last_hashes:
                # First run initialization
                changes_detected.append({
                    "name": name,
                    "url": url,
                    "timestamp": datetime.now().isoformat(),
                    "status": "Initial Check (No history recorded)",
                    "hash_change": f"Initial Hash: {content_hash[:8]}..."
                })
            else:
                print(f"✅ No change for: {name}")

        except requests.exceptions.RequestException as e:
            # Handle connection errors, timeouts, etc.
            print(f"❌ Error checking {name} ({url}): {e}")
            changes_detected.append({
                "name": name,
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "status": f"Error: {e}",
                "hash_change": "N/A"
            })
        
        # Be polite, add a small delay between requests
        time.sleep(1)

    # 5. Save the current hashes for the next run
    with open(HASH_STORAGE_FILE, 'w') as f:
        json.dump(current_hashes, f, indent=4)
        
    return changes_detected

def generate_xml_report(changes):
    """Generates an XML report from the list of detected changes."""
    root = ET.Element("MonitoringReport")
    
    # Add a root status element
    status_tag = ET.SubElement(root, "Status")
    if changes:
        status_tag.text = f"{len(changes)} Change(s) or Initial Check(s) Detected."
    else:
        status_tag.text = "No changes detected since the last run."
        
    ET.SubElement(root, "TimestampGenerated").text = datetime.now().isoformat()

    for change in changes:
        item = ET.SubElement(root, "ChangeItem")
        
        ET.SubElement(item, "Name").text = change["name"]
        ET.SubElement(item, "URL").text = change["url"]
        ET.SubElement(item, "Timestamp").text = change["timestamp"]
        ET.SubElement(item, "Status").text = change["status"]
        ET.SubElement(item, "HashDetails").text = change["hash_change"]

    # Write the XML to file
    tree = ET.ElementTree(root)
    # This function is used for pretty-printing the XML
    ET.indent(tree, space="  ")
    tree.write(XML_OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
    
    print(f"\nReport written to {XML_OUTPUT_FILE}")

if __name__ == "__main__":
    print("--- Web Monitoring Buoy Started ---")
    recent_changes = check_for_changes()
    generate_xml_report(recent_changes)
    print("--- Monitoring Run Complete ---")
