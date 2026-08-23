#include <chrono>
#include <csignal>
#include <cstdlib>
#include <exception>
#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "high_level_base.h"

namespace
{
volatile std::sig_atomic_t keep_running = 1;

void handle_signal(int)
{
  keep_running = 0;
}

void print_usage(const char *program)
{
  std::cout << "Usage: " << program << " [--once] [--interval-ms N]\n";
}

bool parse_positive_interval(const char *value, int &interval_ms)
{
  try
  {
    const auto parsed = std::stoul(value);
    if (parsed == 0 || parsed > 60000)
    {
      return false;
    }
    interval_ms = static_cast<int>(parsed);
    return true;
  }
  catch (const std::exception &)
  {
    return false;
  }
}
}  // namespace

int main(int argc, char **argv)
{
  bool once = false;
  int interval_ms = 1000;

  for (int index = 1; index < argc; ++index)
  {
    const std::string argument(argv[index]);
    if (argument == "--once")
    {
      once = true;
    }
    else if (argument == "--interval-ms" && index + 1 < argc)
    {
      if (!parse_positive_interval(argv[++index], interval_ms))
      {
        std::cerr << "--interval-ms must be in the range [1, 60000].\n";
        return 2;
      }
    }
    else if (argument == "--help" || argument == "-h")
    {
      print_usage(argv[0]);
      return 0;
    }
    else
    {
      std::cerr << "Unknown argument: " << argument << "\n";
      print_usage(argv[0]);
      return 2;
    }
  }

  std::signal(SIGINT, handle_signal);
  std::signal(SIGTERM, handle_signal);

  auto robot = createQuadruped();
  if (!robot)
  {
    std::cerr << "Agibot SDK createQuadruped() returned a null robot instance.\n";
    return 3;
  }

  const int32_t init_result = robot->init();
  if (init_result != 0)
  {
    std::cerr << "Agibot SDK robot->init() failed with code " << init_result << ".\n";
    return 4;
  }

  do
  {
    try
    {
      const Robotstate state = robot->GetRobotStatus();
      (void)state;
      std::cout
        << R"({"event":"telemetry","vendor":"agibot","model":"d1_maxpro","source":"GetRobotStatus"})"
        << std::endl;
    }
    catch (const std::exception &exception)
    {
      std::cerr << "Agibot SDK GetRobotStatus() failed: " << exception.what() << "\n";
      return 5;
    }
    catch (...)
    {
      std::cerr << "Agibot SDK GetRobotStatus() failed with an unknown exception.\n";
      return 5;
    }

    if (!once && keep_running)
    {
      std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));
    }
  } while (!once && keep_running);

  // Destruction owns SDK shutdown. This read-only probe deliberately sends no
  // StopMove, Getdown, Standup, Move, joint, charging, or mode-switch command.
  robot.reset();
  return 0;
}
