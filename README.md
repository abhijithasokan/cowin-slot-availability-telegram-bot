# CoWin Vaccine notifier (Telegram Bot)
During the peak vaccine demand in India, vaccine slots were hard to book as slots got filled like on a black Friday sale.
We worked on making the process of finding vaccines a lot easier. 


The solution had to solve few main problems

1. Users should be able to receive updates when the vaccine is available in their area, thus avoiding the need to constantly log in to CoWin portal. 
2. Users should also get details like vaccine type, which dose is administered and what date the vaccination drive is scheduled. 
    
To make the solution widely available, a telegram bot seemed the most suitable choice.


The bot was build using the official telegram bot framework.
The server side of the bot queried the official CoWin (India's centralized online platform to book vaccine appointments) API periodically and sends the updates to users. 


The bot was initially built to serve family and close friends but soon became available to a wider audience.

## Stats (on 31st Dec 2021 @ 21:37)
<table>
    <tbody>
        <tr> 
            <td> Users at peak </td>
            <td> 1733 </td>
        </tr>
        <tr> 
            <td> Pincodes served </td>
            <td> 581 </td>
        </tr>
        <tr> 
            <td> Broadcasts updates sent so far </td>
            <td> 1.96 M (1,961,394) </td>
        </tr>
    </tbody>
</table>


## Screenshots
<table>
    <thead>
        <tr> 
            <td> Getting Info from user </td>
            <td> User getting updates </td>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>
                <img src='https://user-images.githubusercontent.com/17292384/136824850-0181c24c-4794-4ab6-914e-e292b13bf063.jpg' width="300">
            </td>
            <td>
                <img src='https://user-images.githubusercontent.com/17292384/136824855-28cf1496-f4a2-4f85-ab2f-e915ef2b849c.jpg' width=300>
            </td>
        </tr>
    </tbody>
</table>



## How to run?
1. Install required packages (see requirement.txt for complete list)
    - [Telegram BOT library](https://github.com/python-telegram-bot/python-telegram-bot)
    - SQL DB System - MariaDB, MySQL, or SQLite
    - SQL Alchemy (used as ORM)
2. Generate token for bot with the help from [BotFather](https://core.telegram.org/bots#6-botfather)
3. Provide DB credential via JSON file
    ```json
    {
     "DB_SETTINGS" : {
        "host" : "<db-host-address>",
        "name" : "<db-name>",
        "username" : "<db-username>",
        "password" : "<db-pass>"
        }
    }
    ```
4. Provide Bot Token key and DB credentials via environment variables
    - Bot token - _COWIN_TEL_BOT_KEY_ 
    - DB credentials (path to config in JSON format) - _DB_INFO_FILE_ 
