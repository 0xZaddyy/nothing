# Mario Kart: Double Sats

<img src="https://i.imgur.com/xOA0P7T.png" alt="Mario Kart: Double Sats" width="600">

**Mario Kart: Double Sats** streams sats in real time based on your performance in *Mario Kart: Double Dash*.

## Requirements

- [Dolphin emulator](https://dolphin-emu.org/download/)
- A copy of the [*Mario Kart: Double Dash* ROM](https://romsfun.com/download/mario-kart-double-dash-27533/6)

## Setup

1. Launch the Dolphin emulator and start Double Dash.
   
2. Clone this repo and navigate into the project folder.

3. Set the required environment variables for LND:
   - `GRPC_HOST`: your LND gRPC endpoint (e.g. `localhost:10009`)
   - `ADMIN_MACAROON`: hex-encoded string of your admin macaroon
   - Optionally, put your TLS cert in the root directory as `tls.cert`
  
4. Start the server:
   ```bash
   python mario.py
   
5. Open http://localhost:5000 in your browser and switch to full screen.

6. Run the AutoHotKey script, select the game window, and press Ctrl + M to snap it over the UI.
