#include <stdlib.h>
#include <stdio.h>

#include <inttypes.h>
#include <windows.h>

#include "tobii_research_eyetracker.h"
#include "tobii_research_streams.h"


static void sleep_ms(int time) {
  Sleep(time);
}


void time_synchronization_data_callback(TobiiResearchTimeSynchronizationData* time_synchronization_data, void* user_data) {
  printf("Device time stamp: %" PRId64 "\n", time_synchronization_data->device_time_stamp);
  printf("System request time stamp: %" PRId64 "\n", time_synchronization_data->system_request_time_stamp);
  printf("System response time stamp: %" PRId64 "\n", time_synchronization_data->system_response_time_stamp);
}


void time_synchronization_data(TobiiResearchEyeTracker* eyetracker) {

  char* serial_number = NULL;
  tobii_research_get_serial_number(eyetracker, &serial_number);

  printf("Subscribing to time synchronization data for eye tracker with serial number %s.\n", serial_number);

  tobii_research_free_string(serial_number);

  tobii_research_subscribe_to_time_synchronization_data(eyetracker, time_synchronization_data_callback, NULL);

  /* Wait while some time synchronization data is collected. */
  sleep_ms(2000);

  tobii_research_unsubscribe_from_time_synchronization_data(eyetracker, time_synchronization_data_callback);
  printf("Unsubscribed from time synchronization data.\n");
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

  time_synchronization_data(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
