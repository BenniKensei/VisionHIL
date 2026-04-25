# VisionHIL

## Project Overview
VisionHIL is an automated Hardware-in-the-Loop (HIL) testing framework that uses Computer Vision to physically validate the state of an edge node. It bridges the gap between software logs and physical hardware reality.

## Project Significance
In traditional testing environments, assertions often rely solely on software-level responses. This methodology suffers from the "False Positive" problem: software components may report a successful execution state while the underlying physical hardware (such as LEDs or display screens) fails to respond due to driver faults or hardware malfunctions. VisionHIL resolves this discrepancy by implementing direct optical validation of the hardware, ensuring the physical output strictly aligns with the intended software state.

## Architecture

The system architecture is composed of four primary subsystems:

| Component | Technology | Description |
|-----------|------------|-------------|
| **Orchestration** | Bash | A control script (`run_tests.sh`) responsible for managing background processes, execution flow, and deterministic health-check polling via `curl`. |
| **Edge Node** | Flask | A server simulating a 5G edge node. It binds to local network interfaces to facilitate real-time interactions with physical mobile test devices. |
| **Vision Engine** | OpenCV | Provides hardware state validation using HSV color-space masking. It employs morphological operations (dilation) to reject background noise and handle occlusions caused by on-screen text. |
| **Test Suite** | pytest | An automated testing framework that executes REST API mutations against the edge node and coordinates synchronized optical assertions. |

## Setup Instructions

### 1. Dependency Installation
Initialize the Python environment by installing the required dependencies. Using `python -m pip` ensures the packages are installed into the correct active Python interpreter:

```bash
python -m pip install -r requirements.txt
```

### 2. Network Configuration
The Edge Node server operates on port `5000`. To interface with the simulated node from a physical test client (e.g., a mobile device), ensure the client is connected to the same local network subnet. Access the interface by navigating to the host machine's IP address (e.g., `http://<laptop-ip>:5000`).

## AI Integration
Artificial Intelligence was utilized in the development of this repository for key architectural and tuning decisions:
- **Computer Vision Optimization**: AI systems were leveraged to analyze camera inputs and optimize the HSV threshold boundaries for environmental lighting.
- **Process Management**: The system architecture for Linux process lifecycle management, specifically the implementation of robust teardown routines using `trap` signals to prevent dangling ports and zombie processes, was designed via AI consultation.
