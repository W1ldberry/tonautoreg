# TONautoreg Readme
This is script for TON validator nodes for automatic registration in elections and automatic confirmation by custodians of transactions to the elector smart contract

## Features
 - More reliable than validator_msig.sh
 - Checks wallet balance before transactions
 - Confirms registration with "participant_list" method
 - Telegram and email notifications
 - Fully supports multisig wallets with reqConfirm > 1
 - Auto confirmation of multisig transactions
 - Requests blockchain global configuration parameters (minimal hardcode)
 - Uses tonos-cli

## Requirements
 - python version 3.6.9 or later
 - tonos-cli (use latest version)
 - TON node installed from https://github.com/tonlabs/net.ton.dev (for test network) or https://github.com/tonlabs/main.ton.dev (for main network)

## Autoregistrator installation & configuration
 1. Clone this repository:
```sh
$ cd ~ && git clone -v https://github.com/W1ldberry/tonautoreg.git && cd tonautoreg
```
 2. Open file config.json in any text editor
 3. Change parameters & paths as you want
 4. Install script to cron (examples in cron.example file)
 ```sh
$  crontab -e
```
and paste line below 
```
*/10 * * * *     cd /home/user/tonautoreg && python3 /home/user/tonautoreg/autoreg.py >> /home/user/tonautoreg/status/autoreg.log 2>&1
```
 5. Check logs if something went wrong

## Autoconfirmator installation & configuration
If you have a multisig wallet that requires confirmation of custodians, you can automate the confirmation of these transactions. 
Warning! Autoconfirm.py script only confirms transactions to the elector smart contract!

On the custodian node:
 1. Clone this repository:
```sh
$ cd ~ && git clone -v https://github.com/W1ldberry/tonautoreg.git && cd tonautoreg
```
 2. Open file config.custodian.json in any text editor
 3. Change parameters & paths as you want
 4. Install script to cron (examples in cron.example file)
 ```sh
$  crontab -e
```
and paste line below 
```
*/5 * * * *     cd /home/user/tonautoreg && python3 /home/user/tonautoreg/autoconfirm.py >> /home/user/tonautoreg/status/autoconfirm.log 2>&1
```
 5. Check logs if something went wrong

## Notifications
There are several types of notifications:
1. For validator node owner: 
 - Not enough tokens for transaction/elections
 - Successfully registered in elections
 - Error while sending transaction
2. For custodians:
 - Need confirmation for transaction
 - Transaction successfully confirmed
 
## Email Notifications
For email notifications you need configure "email" section in the config.json or config.custodian.json
```
"email": {
      "login": "myname@gmail.com",
      "password": "mystronpassw0rd",
      "smtp": "smtp.gmail.com",
      "port": 587
  }
```
For using with Gmail you need some extra manipulations as described here https://support.google.com/accounts/thread/12835078?hl=en

Than you can add items in "notifications" section:
```
"custodian public key in hex, starting with 0x": {
  "type": "email",
  "params": {"address": "custodian.name@gmail.com"}
}
```
or
```
"owner": {
  "type": "email",
  "params": {"address": "wallet.owner@gmail.com"}
}
```
## Telegram bot Notifications
For notification in telegram bot you need bot token and chat_id. Ask google "how to get telegram bot token and chat_id" for more info.
Than add items in "notifications" section:
```
"owner": {
  "type": "telegram",
  "params": {"token": "22222222:mytoken", "chat_ids": ["11111111"]}
},
```
