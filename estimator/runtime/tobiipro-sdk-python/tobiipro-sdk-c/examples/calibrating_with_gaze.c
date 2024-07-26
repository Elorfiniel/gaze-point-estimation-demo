#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>

#include <inttypes.h>
#include <windows.h>

#include "tobii_research_eyetracker.h"
#include "tobii_research_calibration.h"
#include "tobii_research_streams.h"


static void sleep_ms(int time) {
  Sleep(time);
}


bool user_looking_at_screen = false;

void gaze_callback(TobiiResearchGazeData* gaze_data, void* user_data) {
  (void)(user_data);
  /* Check if gaze is in the display area so that we can collect calibration data
  once the user is safely looking at the screen. */

  if (user_looking_at_screen) {
    return;
  }

  bool left_eye_on_screen = false;
  bool right_eye_on_screen = false;

  if (gaze_data->left_eye.gaze_point.position_on_display_area.x >= 0.0f &&
    gaze_data->left_eye.gaze_point.position_on_display_area.y >= 0.0f) {
    left_eye_on_screen = true;
  }

  if (gaze_data->right_eye.gaze_point.position_on_display_area.x >= 0.0f &&
    gaze_data->right_eye.gaze_point.position_on_display_area.y >= 0.0f) {
    right_eye_on_screen = true;
  }

  if (left_eye_on_screen && right_eye_on_screen) {
    user_looking_at_screen = true;
  }

  printf("Left eye gaze point: (%f, %f)\nRight eye gaze point: (%f, %f)\n",
    gaze_data->left_eye.gaze_point.position_on_display_area.x,
    gaze_data->left_eye.gaze_point.position_on_display_area.y,
    gaze_data->right_eye.gaze_point.position_on_display_area.x,
    gaze_data->right_eye.gaze_point.position_on_display_area.y);
}

void calibrating_with_gaze(TobiiResearchEyeTracker* eyetracker) {

  /* Subscribe to gaze before starting the calibration and unsubscribe after calibration is done.
  Subscribing and unsubscribing to gaze during the calibration flow will result in undefined
  behavior and should be avoided.
  */

  TobiiResearchStatus status = tobii_research_subscribe_to_gaze_data(eyetracker, gaze_callback, NULL);

  if (status != TOBII_RESEARCH_STATUS_OK) {
    printf("Failed while subscribing to gaze %d", status);
  }

  /* Enter calibration mode. */
  status = tobii_research_screen_based_calibration_enter_calibration_mode(eyetracker);
  char* serial_number = NULL;
  tobii_research_get_serial_number(eyetracker, &serial_number);

  printf("Entered calibration mode for eye tracker with serial number %s. \n", serial_number);

  tobii_research_free_string(serial_number);
  /* Define the points on screen we should calibrate at. */
  /* The coordinates are normalized, i.e. (0.0, 0.0) is the upper left corner and (1.0, 1.0) is the lower right corner. */

  TobiiResearchNormalizedPoint2D point_to_calibrate = { 0.5f, 0.5f };
  printf("Show a point on screen at (%f,%f).\n", point_to_calibrate.x, point_to_calibrate.y);
  printf("Wait for user to look at the screen until we gather calibration data.\n");

  while (!user_looking_at_screen) {
    //  Wait a little bit for the user to focus on the dot until we try again.
    sleep_ms(100);
  }

  printf("Collecting data at (%f,%f).\n", point_to_calibrate.x, point_to_calibrate.y);
  if (tobii_research_screen_based_calibration_collect_data(eyetracker, point_to_calibrate.x, point_to_calibrate.y) != TOBII_RESEARCH_STATUS_OK) {
    /* Try again if it didn't go well the first time. */
    /* Not all eye tracker models will fail at this point, but instead fail on ComputeAndApply. */
    tobii_research_screen_based_calibration_collect_data(eyetracker, point_to_calibrate.x, point_to_calibrate.y);
  }

  printf("Computing and applying calibration.\n");
  TobiiResearchCalibrationResult* calibration_result = NULL;
  status = tobii_research_screen_based_calibration_compute_and_apply(eyetracker, &calibration_result);

  if (status == TOBII_RESEARCH_STATUS_OK && calibration_result->status == TOBII_RESEARCH_CALIBRATION_SUCCESS) {
    printf("Compute and apply returned %i and collected at %zu points.\n", status, calibration_result->calibration_point_count);
  }
  else {
    printf("Calibration failed!\n");
  }

  /* Free calibration result when done using it */
  tobii_research_free_screen_based_calibration_result(calibration_result);
  /* The calibration is done. Leave calibration mode. */
  status = tobii_research_screen_based_calibration_leave_calibration_mode(eyetracker);
  if (status != TOBII_RESEARCH_STATUS_OK) {
    printf("Failed leaving calibration mode %d.\n", status);
  }
  else {
    printf("Left calibration mode.\n");
  }

  /* Unsubscribe to gaze after calibration is done.*/
  status = tobii_research_unsubscribe_from_gaze_data(eyetracker, gaze_callback);
  if (status != TOBII_RESEARCH_STATUS_OK) {
    printf("Failed unsubscribing to gaze %d.\n", status);
  }
  else {
    printf("Unsubscribed to gaze.\n");
  }
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

  calibrating_with_gaze(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
