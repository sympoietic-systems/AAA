import sys
from fastapi.testclient import TestClient

# Ensure backend package can be imported
sys.path.insert(0, ".")

from backend.main import app

def test_file_endpoints():
    with TestClient(app) as client:
        # 1. Upload a mock text file
        mock_file_data = b"This is a mock text file content for indexing and summarization."
        files = {
            "files": ("mock_file.txt", mock_file_data, "text/plain")
        }
        
        response = client.post("/api/conversations/new/files", files=files)
        print("Upload Status:", response.status_code)
        assert response.status_code == 200
        
        data = response.json()
        conversation_id = data["conversation_id"]
        assert conversation_id is not None
        assert len(data["files"]) == 1
        assert data["files"][0]["file_name"] == "mock_file.txt"
        assert data["files"][0]["status"] == "uploading"
        print(f"File uploaded to conversation: {conversation_id}")
        
        # 2. Get conversation files
        response = client.get(f"/api/conversations/{conversation_id}/files")
        print("Get Files Status:", response.status_code)
        assert response.status_code == 200
        files_data = response.json()
        assert len(files_data["files"]) >= 1
        # The file might already have transitioned to processing or ready
        file_record = next(f for f in files_data["files"] if f["file_name"] == "mock_file.txt")
        print(f"File status in DB: {file_record['status']}")
        
        # 2b. Reprocess the file
        response = client.post(f"/api/conversations/{conversation_id}/files/mock_file.txt/reprocess")
        print("Reprocess File Status:", response.status_code)
        assert response.status_code == 200
        
        # 3. Clean up / Delete conversation file
        response = client.delete(f"/api/conversations/{conversation_id}/files/mock_file.txt")
        print("Delete File Status:", response.status_code)
        assert response.status_code == 200
        
        # 4. Verify file is deleted
        response = client.get(f"/api/conversations/{conversation_id}/files")
        files_data = response.json()
        assert not any(f["file_name"] == "mock_file.txt" for f in files_data["files"])
        print("File verified deleted successfully!")

if __name__ == "__main__":
    test_file_endpoints()
    print("All file API integration tests passed!")
