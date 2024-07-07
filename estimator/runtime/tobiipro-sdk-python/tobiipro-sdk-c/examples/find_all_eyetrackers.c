#include <stdlib.h>
#include <stdio.h>

#include "tobii_research.h"
#include "tobii_research_eyetracker.h"


TobiiResearchStatus find_all_eyetrackers() {

  TobiiResearchEyeTrackers* eyetrackers = NULL;

  TobiiResearchStatus result;
  size_t i = 0;

  result = tobii_research_find_all_eyetrackers(&eyetrackers);
  if (result != TOBII_RESEARCH_STATUS_OK) {
    printf("Finding trackers failed. Error: %d\n", result);
    return result;
  }

  for (i = 0; i < eyetrackers->count; i++) {
    TobiiResearchEyeTracker* eyetracker = eyetrackers->eyetrackers[i];
    char* address = NULL;
    char* serial_number = NULL;
    char* device_name = NULL;

    tobii_research_get_address(eyetracker, &address);
    tobii_research_get_serial_number(eyetracker, &serial_number);
    tobii_research_get_device_name(eyetracker, &device_name);

    printf("%s\t%s\t%s\n", address, serial_number, device_name);

    tobii_research_free_string(address);
    tobii_research_free_string(serial_number);
    tobii_research_free_string(device_name);
  }
  printf("Found %d Eye Trackers \n\n", (int)eyetrackers->count);
  tobii_research_free_eyetrackers(eyetrackers);

  return result;
}


int main(int argc, char* argv[]) {
  find_all_eyetrackers();
  return EXIT_SUCCESS;
}
