import os
import sys

# Add the api directory to Python path
api_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, api_dir)

# Now run the server
import uvicorn

if __name__ == "__main__":
    os.chdir(api_dir)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
