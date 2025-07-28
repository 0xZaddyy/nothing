# Mario Kart: Double Sats

<img src="https://i.imgur.com/xOA0P7T.png" alt="Mario Kart: Double Sats" width="600">

**Mario Kart: Double Sats** streams sats in real time based on your performance in *Mario Kart: Double Dash*.

## Gameplay Examples
- [Tokyo Bitcoin Base - behind the scenes](https://primal.net/e/nevent1qqsgka556y0sc54wxjlzyqgrd6c5g8qyqjskk3x24cn5e0np0y529scl7m27u)
- [Tokyo Bitcoin Base - promo video](https://x.com/TYO_BitcoinBase/status/1940076786953711656)

## Requirements

- Windows or Linux (MacOS is _not supported_)
- [Dolphin emulator](https://dolphin-emu.org/download/)
- A copy of the [*Mario Kart: Double Dash* ROM](https://romsfun.com/download/mario-kart-double-dash-27533/6)*
- LND or Phoenixd

*\* Important: Make sure you're using the USA version of the ROM, which should be exactly 377 MB. If you use a different version, the game will not work!*

## Setup

1. Launch the Dolphin emulator and start Double Dash.
   
2. Clone this repo and navigate into the project folder.

3. Set the required variables in your OS environment for your choice of funding source.

   For LND:
   - `FUNDING_SOURCE=lnd`
   - `GRPC_HOST`: your LND gRPC endpoint (e.g. `localhost:10009`)
   - `ADMIN_MACAROON`: hex-encoded string of your admin macaroon
   - Optionally, put your TLS cert in the root directory as `tls.cert`

   For Phoenixd:
   - `FUNDING_SOURCE=phoenixd`
   - `PHOENIXD_HOST_URL`
   - `PHOENIXD_HTTP_USER`
   - `PHOENIXD_HTTP_PASSWORD`
  
5. Start the server:
   ```bash
   python mario.py
   
6. Open http://localhost:5000 in your browser and switch to full screen.

7. Run the [AutoHotKey](https://www.autohotkey.com/) script, select the game window, and press Ctrl + M to snap it over the UI.

<img src=https://github.com/dplusplus1024/satoshi-speedway/blob/main/screenshot.png>
