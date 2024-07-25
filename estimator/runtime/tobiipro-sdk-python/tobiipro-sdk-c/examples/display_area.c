#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "tobii_research_eyetracker.h"

void get_display_area(TobiiResearchEyeTracker* eyetracker) {

  TobiiResearchDisplayArea display_area;
  TobiiResearchStatus status = tobii_research_get_display_area(eyetracker, &display_area);

  char* serial_number = NULL;
  tobii_research_get_serial_number(eyetracker, &serial_number);

  printf("Got display area from tracker with serial number %s with status %i:\n", serial_number, status);
  tobii_research_free_string(serial_number);

  printf("Height: %f\n", display_area.height);
  printf("Width: %f\n", display_area.width);

  printf("Bottom Left: (%f, %f, %f)\n",
          display_area.bottom_left.x,
          display_area.bottom_left.y,
          display_area.bottom_left.z);
  printf("Bottom Right: (%f, %f, %f)\n",
          display_area.bottom_right.x,
          display_area.bottom_right.y,
          display_area.bottom_right.z);
  printf("Top Left: (%f, %f, %f)\n",
          display_area.top_left.x,
          display_area.top_left.y,
          display_area.top_left.z);
  printf("Top Right: (%f, %f, %f)\n",
          display_area.top_right.x,
          display_area.top_right.y,
          display_area.top_right.z);

  // To set the display area it is possible to either use a previously saved instance of
  // the type TobiiResearchDisplayArea, or create a new one as shown below.
  TobiiResearchDisplayArea new_display_area;
  // For simplicity we are using the same values that are already set on the eye tracker.
  memcpy(&new_display_area.top_left, &display_area.top_left, sizeof(display_area.top_left));
  memcpy(&new_display_area.top_right, &display_area.top_right, sizeof(display_area.top_right));
  memcpy(&new_display_area.bottom_left, &display_area.bottom_left, sizeof(display_area.bottom_left));

  status = tobii_research_set_display_area(eyetracker, &new_display_area);
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

  get_display_area(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
