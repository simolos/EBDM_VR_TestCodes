# EBDM_VR_TestCodes

# Setup:

1. Install required Python packages in the virtual environment:
   pip install numpy websockets uvicorn fastapi

2. Start the WebSocket server:
   uvicorn websocket_server:app --host 127.0.0.1 --port 8765 --log-level info
   (Keep this terminal open — the server must be running to stream events.)

3. In a second terminal, activate the virtual environment:
   source /path/to/venv/bin/activate

4. In the same terminal, run the test scripts 

