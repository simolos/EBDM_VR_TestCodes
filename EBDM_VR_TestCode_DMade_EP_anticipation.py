
import time
import random
import numpy as np
from ws_stream import TrialStreamer  # assuming this is the module you have

# Initialize the streamer
streamer = TrialStreamer("ws://127.0.0.1:8765/trials")
streamer.start()

try:
    # Wait 1 seconds before starting the trial
    print("Waiting 1 seconds before trial_beginning...")
    time.sleep(1)
    
    # Preparation to the DM phase
    dur_Prep_DM = random.uniform(1, 1.4)
    print("Preparation to the DM phase")
    streamer.send_event("PrepDM", {"dur_PrepDM": round(dur_Prep_DM, 2)})
    time.sleep(dur_Prep_DM)

    # Beginning of the DM phase (Offer Presentation)
    dur_DMphase = 4 # seconds, this is the maximum duration of the phase!! but if the decision is made before the timeout (i.e., if you receive the next trigger within 4s), we move on to the DecisionFeedback phase
    EffortLevel = 0.95 # it means that the door has to be already open for 5% and the rest will be opened through effort exertion
    RewardLevel = 1 # level 1 out of 4 (e.g. for rewards [1 5 10 20 cents], this would be 20 cents. for entertaining reward, this would be a specific video. the information will be taken out of a config file)
    print("DM phase (offer presentation) - max duration 4s")
    streamer.send_event("DMphase", {"dur_DMphase": dur_DMphase, "Effort": EffortLevel, "Reward": RewardLevel})

    # DecisionFeedback phase 
    time.sleep(2) # e.g. decision made in 2s
    print("DecisionFeedback")
    DMFeedback = 1 # 1 is yes, 0 is no
    dur_DecisionFeedback = 1 # s
    streamer.send_event("DecisionFeedback", {"DMFeedback": DMFeedback, "dur_DecisionFeedback": dur_DecisionFeedback}) # --> this means show the corresponding decision for dur_Feedback
    time.sleep(dur_DecisionFeedback) 

    # Preparation to the EP phase
    dur_Prep_EP = random.uniform(1, 1.4)
    print("Preparation to the EP phase")
    streamer.send_event("PrepEP", {"dur_PrepEP": round(dur_Prep_EP, 2)})
    time.sleep(dur_Prep_EP)


    # Preparation to the EP Feedback phase 
    dur_Prep_EPFeedback = random.uniform(1)
    print("Preparation to the EPFeedback phase")
    streamer.send_event("PrepEP", {"dur_Prep_EPFeedback": dur_Prep_EPFeedback})
    time.sleep(dur_Prep_EPFeedback)

    
    # EPFeedback phase
    EPFeedback = -1 # 1 is success, 0 is failure, -1 is anticipation
    print("EPFeedback")
    dur_EPFeedback = 1 # s
    streamer.send_event("EPFeedback", {"EPFeedback": EPFeedback, "dur_EPFeedback": dur_EPFeedback}) # --> this means show the corresponding decision for dur_Feedback
    time.sleep(dur_DecisionFeedback) 


    # ITI (intertrial interval)
    DurITI = 2
    streamer.send_event("ITI", {"DurITI": DurITI}) 
    time.sleep(2) 

    print("End of the trial")



finally:
    # Close the streamer at the end
    print("Closing streamer")
    streamer.close()

