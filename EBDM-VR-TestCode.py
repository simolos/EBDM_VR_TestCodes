
# Run: pip install numpy websockets uvicorn fastapi
# Run uvicorn websocket_server:app --host 127.0.0.1 --port 8765 --log-level info
# In a second terminal, activate the venv: source "venv_path"/bin/activate


import time
import random
import numpy as np
from ws_stream import TrialStreamer  # assuming this is the module you have

# Initialize the streamer
streamer = TrialStreamer("ws://127.0.0.1:8765/trials")
streamer.start()

try:
    # Wait 3 seconds before starting the trial
    print("Waiting 1 seconds before trial_beginning...")
    time.sleep(1)
    
    # Preparation to the DM phase
    dur_Prep_DM = random.uniform(1, 1.4)
    print("Preparation to the DM phase")
    streamer.send_event("PrepDM", {"dur_PrepDM": dur_Prep_DM})
    time.sleep(dur_Prep_DM)

    # Beginning of the DM phase (Offer Presentation)
    dur_DMphase = 4 # seconds, this is the maximum duration of the phase!! but if the decision is made before the timeout (i.e., if you receive the next trigger within 4s), we move on to the DecisionFeedback phase
    EffortLevel = 4 # Percentage --> it means that the door has to be already open for 5% and the rest will be opened through effort exertion
    RewardLevel = 1 # level 1 out of 4 (e.g. for rewards [1 5 10 20 cents], this would be 20 cents. for entertaining reward, this would be a specific video. the information will be taken out of a config file)
    print("Offer presentation - max duration 4s")
    streamer.send_event("StartDM", {"dur_DMphase": dur_DMphase, "Effort": EffortLevel, "Reward": RewardLevel})

    # DecisionFeedback phase 
    time.sleep(2) # e.g. decision made in 2s
    print("DecisionFeedback")
    choice = 1 # 1 is yes, 0 is no
    dur_Feedback = 1
    streamer.send_event("DecisionMade", {"choice": choice, "dur_Feedback": dur_Feedback}) # --> this means show the corresponding decision for dur_Feedback
    time.sleep(dur_Feedback) 

    # ITI (intertrial interval)
    DurITI = 2
    streamer.send_event("ITI", {"DurITI": DurITI}) 
    time.sleep(2) 

    print("End of the trial")



finally:
    # Close the streamer at the end
    print("Closing streamer")
    streamer.close()

# --------- Example: how to integrate in PsychoPy main loop ---------
#
# streamer = TrialStreamer("ws://127.0.0.1:8765/trials")
# streamer.start()
#
# # After initialisation
# streamer.send_array("Trials", trials.astype("float32"), trial=i,
#                     meta={"fs": 50.0, "label": "Ypos"})
#
# # When a trial starts
# streamer.send_event("trial_start", {"t0": expClock.getTime()})
#
# # After decision
# streamer.send_event("decision", {"trial": i, "choice": choice, "rt_ms": rt_ms})
#
# # Effort phase start
# streamer.send_event("effort_start", {"trial": i, "t_ms": 0.0})
#
# # During effort (e.g., at ~50 Hz), push a small window of cursor samples (binary)
# # CURSOR is (N,2) or (N,) ndarray
# streamer.send_array("cursor_trace", CURSOR.astype("float32"), trial=i,
#                     meta={"fs": 50.0, "label": "Ypos"})
#
# # Effort end
# streamer.send_event("effort_end", {"trial": i, "success": int(success), "peak": float(peak), "duration_ms": dur_ms})
#
# # Feedback & trial end
# streamer.send_event("feedback", {"trial": i, "gain": float(gain)})
# streamer.send_event("trial_end", {"trial": i, "t1": expClock.getTime()})
#
# # At the end
# streamer.close()