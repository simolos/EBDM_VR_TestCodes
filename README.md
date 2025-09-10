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


# Scripts description: 
1. EBDM_VR_TestCode_DMTimeout.py: the decision is not made before the timeout
2. EBDM_VR_TestCode_DMade_NOEP.py: the decision is made but the effort is not required (either because the decision is no or for experimental reason)
3. EBDM_VR_TestCode_DMade_EP.py: the decision is yes and the effort is required and well exerted
4. EBDM_VR_TestCode_DMade_EP.py: the decision is yes and the effort is required but the subject anticipates the effort production --> failure



