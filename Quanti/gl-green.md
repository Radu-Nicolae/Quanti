# Usage Guide
This guide provides essential information on how to use the provisioned server effectively.

## 1. Connecting to your machine

You now have two options for connecting.

### Option 1 — Direct SSH Command

Run:
```bash
ssh -J gl_green@145.108.225.3:42224 gl_green@glg1
```
### Option 2 — SSH Config Setup (recommended)

Add the following to your `~/.ssh/config` file:

```plaintext
Host glgate
    Hostname 145.108.225.3
    Port 42224
    User gl_green
    IdentityFile ~/.ssh/<your_private_key>
    IdentitiesOnly yes

Host glg1
    User gl_green
    ProxyJump glgate
```

Then connect with:
```bash
ssh glg1
```

## 2. Copying files to the server

When transferring files, you must use scp -O to ensure compatibility with the jump host:
```bash
scp -O local_file glg1:/path/on/server
```

Example:
```bash
scp -O files.tar.gz glg1:~/
```
## 3. Booking Policy

You may use a machine without booking only if there is no current experiment running on it.

However, for experiments, you must create a booking so the machine is reserved exclusively for you, and all other processes are cleared before your session.

## 4. Creating a booking

Run:
```bash
ssh gl_green@145.108.225.3 -p 42224 booking create ...
```
Usage:
```plaintext
booking create [-h] machines start_time duration

positional arguments:
  machines    Comma-separated list of machine names
  start_time  Format: DD-MM-YYYY:HH (Europe/Amsterdam timezone)
  duration    Duration in hours (integer)

options:
  -h, --help  Show this help message and exit
```

Example:
To book glg1 today from 22:00 for 10 hours:
```bash
ssh gl_green@145.108.225.3 -p 42224 booking create glg1 08-08-2025:22 10
```

## 5. Managing bookings
List your bookings

```bash
ssh gl_green@145.108.225.3 -p 42224 booking list
```

Remove a booking

```bash
ssh gl_green@145.108.225.3 -p 42224 booking remove <booking_id>
```

## 6. Provided Toolkit

The following software is available for you on the server based on your project needs:

- Ollama (check `ollama --help` for usage, some models are pre-downloaded and can be checked with `ollama list`)
- Energibridge (check `energibridge --help` for usage)

If you need additional software, please contact the Green Lab team or me directly at a.dragomir@student.vu.nl

## 7. Important notes

You are only allowed to make **one booking** at a time. Plan your experiments in advance to avoid conflicts.

The [Green Lab Calendar](https://calendar.google.com/calendar/embed?src=c_0dd53a7c16fe79fc7e8a1565bd3b8fedfc98ccb502de9b933e21e6d858a60777%40group.calendar.google.com&ctz=Europe%2FAmsterdam) now serves only as an overview of all bookings.

Do not run experiments without a booking:

    You may have other users working on the machine, which can skew results.

    With a booking, the system ensures:

        You have exclusive access during your slot.

        All other users’ processes are terminated before your session.

In contrast, if you are working without a booking and someone else’s booked session starts:

    All your processes (including SSH connections) will be terminated.

    You’ll get a 30-minute advance warning in your terminal.