#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include <inttypes.h>
#include <windows.h>

#include "tobii_research_eyetracker.h"
#include "tobii_research_streams.h"


static void sleep_ms(int time) {
  Sleep(time);
}


void user_position_guide_callback(TobiiResearchUserPositionGuide* user_position_guide, void* user_data) {
  memcpy(user_data, user_position_guide, sizeof(*user_position_guide));
}

void user_position_guide(TobiiResearchEyeTracker* eyetracker) {

  TobiiResearchUserPositionGuide user_position_guide;
  char* serial_number = NULL;
  tobii_research_get_serial_number(eyetracker, &serial_number);

  printf("Subscribing to user position guide for eye tracker with serial number %s.\n", serial_number);

  tobii_research_free_string(serial_number);

  TobiiResearchStatus status = tobii_research_subscribe_to_user_position_guide(eyetracker,
    user_position_guide_callback, &user_position_guide);

  if (status != TOBII_RESEARCH_STATUS_OK)
    return;

  /* Wait while some user position guide is collected. */
  sleep_ms(2000);

  status = tobii_research_unsubscribe_from_user_position_guide(eyetracker, user_position_guide_callback);
  printf("Unsubscribed from user position guide with status %i.\n", status);

  printf("Last received gaze package:\n");

  printf("Left eye 3D gaze point user position: (%f, %f, %F)\n",
    user_position_guide.left_eye.user_position.x,
    user_position_guide.left_eye.user_position.y,
    user_position_guide.left_eye.user_position.z);

  printf("Right eye 3D gaze point user position: (%f, %f, %f)\n",
    user_position_guide.right_eye.user_position.x,
    user_position_guide.right_eye.user_position.y,
    user_position_guide.right_eye.user_position.z);

  /* Wait while some data is collected. */
  sleep_ms(2000);
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

  user_position_guide(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
