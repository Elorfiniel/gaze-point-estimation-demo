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


void gaze_data_callback(TobiiResearchGazeData* gaze_data, void* user_data) {
  memcpy(user_data, gaze_data, sizeof(*gaze_data));

  printf("%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\n",
    gaze_data->left_eye.pupil_data.diameter,
    gaze_data->right_eye.pupil_data.diameter,
    gaze_data->left_eye.gaze_point.position_on_display_area.x,
    gaze_data->left_eye.gaze_point.position_on_display_area.y,
    gaze_data->right_eye.gaze_point.position_on_display_area.x,
    gaze_data->right_eye.gaze_point.position_on_display_area.y
  );
}

void gaze_data(TobiiResearchEyeTracker* eyetracker) {

  TobiiResearchGazeData gaze_data;
  char* serial_number = NULL;
  tobii_research_get_serial_number(eyetracker, &serial_number);

  printf("Subscribing to gaze data for eye tracker with serial number %s.\n", serial_number);

  tobii_research_free_string(serial_number);

  TobiiResearchStatus status = tobii_research_subscribe_to_gaze_data(eyetracker, gaze_data_callback, &gaze_data);

  if (status != TOBII_RESEARCH_STATUS_OK)
    return;

  /* Wait while some gaze data is collected. */
  sleep_ms(4000);

  status = tobii_research_unsubscribe_from_gaze_data(eyetracker, gaze_data_callback);
  printf("Unsubscribed from gaze data with status %i.\n", status);

  printf("Last received gaze package:\n");
  printf("System time stamp: %"  PRId64 "\n", gaze_data.system_time_stamp);
  printf("Device time stamp: %"  PRId64 "\n", gaze_data.device_time_stamp);
  printf("Left eye 2D gaze point on display area: (%f, %f)\n",
    gaze_data.left_eye.gaze_point.position_on_display_area.x,
    gaze_data.left_eye.gaze_point.position_on_display_area.y);
  printf("Right eye 3D gaze origin in user coordinates (%f, %f, %f)\n",
    gaze_data.right_eye.gaze_origin.position_in_user_coordinates.x,
    gaze_data.right_eye.gaze_origin.position_in_user_coordinates.y,
    gaze_data.right_eye.gaze_origin.position_in_user_coordinates.z);

  /* Wait while some gaze data is collected. */
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

  gaze_data(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
