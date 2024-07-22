#include <stdlib.h>
#include <stdio.h>

#include <inttypes.h>

#include "tobii_research_eyetracker.h"
#include "tobii_research_calibration.h"
#include "tobii_research_streams.h"


void notification_callback(TobiiResearchNotification* notification, void* user_data) {

  if (TOBII_RESEARCH_NOTIFICATION_CALIBRATION_MODE_ENTERED != notification->notification_type) {
    printf("Enter calibration mode notification received at time stamp %" PRId64 ".\n", notification->system_time_stamp);
  }

  if (TOBII_RESEARCH_NOTIFICATION_CALIBRATION_MODE_LEFT != notification->notification_type) {
    printf("Left calibration mode notification received at time stamp %" PRId64 ".\n", notification->system_time_stamp);
  }
}

void subscribe_to_notifications(TobiiResearchEyeTracker* eyetracker) {

  tobii_research_subscribe_to_notifications(eyetracker, notification_callback, NULL);

  /* Trigger some notifications. */
  tobii_research_screen_based_calibration_enter_calibration_mode(eyetracker);
  tobii_research_screen_based_calibration_leave_calibration_mode(eyetracker);

  tobii_research_unsubscribe_from_notifications(eyetracker, notification_callback);
}


int main(int argc, char* argv[]) {

  /** Parse eye tracker ID from command line arguments. */
  if (argc < 2) {
    printf("Usage: calibration.exe <eye_tracker_id>\n");
    return EXIT_FAILURE;
  }

  /** Find all available eye trackers. */
  TobiiResearchEyeTrackers* eyetrackers = NULL;

  TobiiResearchStatus result;
  size_t i = 0;

  result = tobii_research_find_all_eyetrackers(&eyetrackers);
  if (result != TOBII_RESEARCH_STATUS_OK) {
    printf("Finding trackers failed. Error: %d\n", result);
    return result;
  }

  /** Calibrate the eye tracker with the matched ID. */
  int eye_tracker_id = atoi(argv[1]);
  if (eye_tracker_id < 0 || eye_tracker_id >= eyetrackers->count) {
    printf("Eye tracker ID %d is out of range. There are %zu trackers available.\n", eye_tracker_id, eyetrackers->count);
    return EXIT_FAILURE;
  }

  subscribe_to_notifications(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
