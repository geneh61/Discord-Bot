from operator import is_
import os
import time
import json
from copy import copy
import discord
import asyncio
import requests
import unicodedata
from bs4 import BeautifulSoup
from discord.ext import commands
from discord.ext import tasks
from dotenv import load_dotenv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

global is_active
is_active = 0

def simplify(s):
	return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def getNextUFC():
    PATH = "C:\Program Files (x86)\chromedriver.exe"
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(PATH, options=chrome_options)

    driver.get("https://www.bestfightodds.com/")

    ufcchild = driver.find_element(By.XPATH, "//h1[contains(text(), 'UFC')]")
    ufclink = driver.find_element(By.PARTIAL_LINK_TEXT, "UFC")
    global ufcevent
    ufcevent = ufcchild.text
    ufclink.click()

    elementtable = driver.find_element(By.CLASS_NAME, "table-inner-wrapper")

    deleteline = ('+','-','▲','▼','DraftKings','1','2','3','4','5','6','7','8','9','0')

    splittable = elementtable.text.splitlines()
    for line in splittable[:]:
        if line.startswith(deleteline):
            splittable.remove(line)

    resulttable = []
    for line in splittable:
        if line.find("+") != -1:
            index = line.find("+")
        else:
            index = line.find("-")
        try:
            resulttable.append(line[:index + 4])
        except:
            resulttable.append(line[:index + 3])
    
    singlestring = ''
    for element in resulttable:
        singlestring += (f"{element.ljust(35)}{resulttable.index(element) + 1}\n")
        if (resulttable.index(element) + 1) % 2 == 0:
            singlestring += '------------------------------------\n'
    return singlestring, resulttable

def getUFCBet():
    return

def oddsToDecimal(odds):
    if odds > 0:
        decimal = (odds / 100) + 1
    else:
        decimal = (100 / abs(odds)) + 1
    return decimal

def main():
    client = commands.Bot(command_prefix = '!')

    load_dotenv()

    @client.event
    async def on_ready():
        print(f"{client.user.name} has connected to Discord")

    # @client.event
    # async def on_message(ctx):
    #     if (ctx.content.startswith("test")):
    #         await ctx.channel.send("success")

    @client.command()
    async def ping(ctx):
        """test command"""
        await ctx.send("Pong")

    @client.command()
    async def ufc(ctx):
        "Displays next upcoming UFC fights, odds, and indices."
        await ctx.send(f"```{ufcstring}```")

    @client.command()
    async def stats(ctx):
        "Displays user betting stats."
        await open_account(ctx.author)
        users = await get_user_stats()

        balance = users[str(ctx.author.id)]["balance"]

        em = discord.Embed(title = f"{ctx.author.name}'s stats")
        em.add_field(name = "Balance", value = balance)
        em.add_field(name = "Total Wagered|Under|Over", value = f'{users[str(ctx.author.id)]["totalWagered"]}|{users[str(ctx.author.id)]["underWagered"]}|{users[str(ctx.author.id)]["overWagered"]}')
        em.add_field(name = "Total Won", value = users[str(ctx.author.id)]["totalWon"])
        em.add_field(name = "Percent return", value = f'%{users[str(ctx.author.id)]["returnRate"]}')
        em.add_field(name = "# of Bets Won/Made", value = f"{users[str(ctx.author.id)]['wonBets']}/{users[str(ctx.author.id)]['numBets']}")
        em.add_field(name = "Percent of Bets won", value = f'%{users[str(ctx.author.id)]["winrate"]}')
        
        if users[str(ctx.author.id)]["numBets"] == 0:
            em.add_field(name = "Average Overdog Odds Taken (Adjusted)", value = "No Odds Taken")
            em.add_field(name = "Average Underdog Odds Taken (Adjusted)", value = "No Odds Taken")
        else:
            em.add_field(name = "Average Overdog(-) Odds Taken (Adjusted)", value = users[str(ctx.author.id)]["overOdds"])
            em.add_field(name = "Average Underdog(+) Odds Taken (Adjusted)", value = users[str(ctx.author.id)]["underOdds"])

        await ctx.send(embed = em)

    @client.command()
    async def payout(ctx, argument):
        users = await get_user_stats()
        for user in users.keys():
            users[user]["balance"] += int(argument)
        await ctx.send(f'{int(argument)} has been paid out to all users.')
        with open("storedbets.json", "w") as f:
            json.dump(users, f)

    async def updateUFC():
        await client.wait_until_ready()
        global ufcstring, ufctable
        while not client.is_closed():
            try:
                ufcstring, ufctable = getNextUFC()
                await results()
                await payoutUFC()
                await asyncio.sleep(3600)
            except Exception as e:
                print(e)
                await asyncio.sleep(3600)
    
    async def payoutUFC():
        ctx = client.get_channel(id=1009272522736410714) # channel id
        users = await get_user_stats()
        userscopy = await get_user_stats()
        copytwo = await get_user_stats()
        if ufcevent != prev_event:
            for user in users.keys():
                for fighter in users[user]["bets"]["events"][prev_event].keys():


                    if fighter.find("+") != -1:
                        cancelled = []
                        cancelledodds = []
                        fighterlist = fighter.split("+")
                        ufcparlayresult = False
                        for indivfighter in fighterlist:
                            if indivfighter in ufcloser:
                                ufcparlayresult = False
                                break
                            elif indivfighter in ufcwinner:
                                ufcparlayresult = True
                                continue
                            else:
                                cancelled.append(indivfighter)
                                for ifighter in users[user]["bets"]["events"][prev_event][fighter].keys():
                                    if indivfighter == ifighter:
                                        cancelledodds.append(users[user]["bets"]["events"][prev_event][fighter][ifighter])

                        #define odds here
                        odds = list(users[user]["bets"]["events"][prev_event][fighter].keys())[0]
                        odds = int(odds)
                        bet = list(users[user]["bets"]["events"][prev_event][fighter].values())[0]
                        bet = int(bet)
                        decimal = oddsToDecimal(int(odds))
                        em = discord.Embed(title = f"{await client.fetch_user(int(user))}'s parlay result")
                        em.add_field(name="Fighter", value = fighter)
                        newodds = 1
                        for a in cancelledodds:
                            temp = oddsToDecimal(int(a))
                            newodds *= temp
                        amerodds = decimal / newodds
                        if amerodds >= 2:
                            amerodds = ((amerodds - 1) * 100)
                        else:
                            amerodds = (-100 / (amerodds - 1))
                        added_odds = []
                        for eodds in range(1, fighter.count('+') + 2):
                            if list(users[user]["bets"]["events"][prev_event][fighter].keys())[-eodds].lstrip('-').isdigit() == True:
                                added_odds.append(list(users[user]["bets"]["events"][prev_event][fighter].keys())[-eodds])
                            else:
                                break
                        added_wagers = []
                        added_decimal = []
                        added_oddsB = []
                        for i in added_odds:
                            added_wagers.append(users[user]["bets"]["events"][prev_event][fighter][i])
                        for a in added_odds:
                            temp = oddsToDecimal(int(a))
                            added_decimal.append(temp / newodds)
                        for i in added_decimal:
                            if i >= 2:
                                added_oddsB.append((i - 1) * 100)
                            else:
                                added_oddsB.append(-100 / (i - 1))
                                
                        if ufcparlayresult == True and len(cancelled) > 0:
                            em.add_field(name = "Parlay Result", value = "Won")
                            em.add_field(name = "Odds Taken", value = round(amerodds)) #need to define odds
                            em.add_field(name = "Wagered", value = bet)
                            em.add_field(name = "Payout", value = round(bet * decimal / newodds))
                            em.add_field(name = "Profit/Loss", value = round((bet * decimal / newodds) - bet))

                            for i in range(len(added_odds)):
                                em.add_field(name = "Additional Odds Taken", value = added_oddsB[i])
                                em.add_field(name = "Additional Wagered", value = added_wagers[i])
                                em.add_field(name = "Payout", value = round(added_wagers[i] * added_decimal[i] / newodds))
                                copytwo[user]["wonBets"] += 1
                                copytwo[user]["totalWon"] += round(added_wagers[i] * added_decimal[i] / newodds)
                                copytwo[user]["balance"] += round(added_wagers[i] * added_decimal[i] / newodds)

                            copytwo[user]["wonBets"] += 1
                            copytwo[user]["totalWon"] += round(bet * decimal / newodds)
                            copytwo[user]["balance"] += round(bet * decimal / newodds)

                        elif ufcparlayresult == True:
                            em.add_field(name = "Parlay Result", value = "Won")
                            em.add_field(name = "Odds Taken", value = round(odds))
                            em.add_field(name = "Wagered", value = bet)
                            em.add_field(name = "Payout", value = round(bet * decimal))
                            em.add_field(name = "Profit/Loss", value = round(bet * decimal - bet))

                            for i in range(len(added_odds)):
                                em.add_field(name = "Additional Odds Taken", value = added_oddsB[i])
                                em.add_field(name = "Additional Wagered", value = added_wagers[i])
                                em.add_field(name = "Payout", value = round(added_wagers[i] * added_decimal[i] / newodds))
                                copytwo[user]["wonBets"] += 1
                                copytwo[user]["totalWon"] += round(added_wagers[i] * added_decimal[i] / newodds)
                                copytwo[user]["balance"] += round(added_wagers[i] * added_decimal[i] / newodds)
                            
                            copytwo[user]["wonBets"] += 1
                            copytwo[user]["totalWon"] += round(bet * decimal / newodds)
                            copytwo[user]["balance"] += round(bet * decimal / newodds)

                        elif ufcparlayresult == False and len(cancelled) < fighter.count("+") + 1:
                            em.add_field(name = "Parlay Result", value = "Lost")
                            em.add_field(name = "Odds Taken", value = round(odds))
                            em.add_field(name = "Wagered", value = bet)
                            em.add_field(name = "Payout", value = 0)
                            em.add_field(name = "Profit/Loss", value = -abs(bet))

                            for i in range(len(added_odds)):
                                em.add_field(name = "Additional Odds Taken", value = added_oddsB[i])
                                em.add_field(name = "Additional Wagered", value = added_wagers[i])
                                em.add_field(name = "Payout", value = 0)

                        else: # all parlay cancelled
                            em.add_field(name = "Parlay Result", value = "Cancelled")
                            em.add_field(name = "Odds Taken", value = round(odds))
                            em.add_field(name = "Wagered", value = bet)
                            em.add_field(name = "Payout", value = bet)
                            em.add_field(name = "Profit/Loss", value = 0)
                            copytwo[user]["totalWagered"] -= bet
                            copytwo[user]["numBets"] -= 1
                            copytwo[user]["balance"] += bet
                            if int(odds) < 0:
                                copytwo[user]["overWagered"] -= bet
                            else:
                                copytwo[user]["underWagered"] -= bet

                            for i in range(len(added_odds)):
                                em.add_field(name = "Additional Odds Taken", value = added_oddsB[i])
                                em.add_field(name = "Additional Wagered", value = added_wagers[i])
                                em.add_field(name = "Payout", value = added_wagers[i])
                                copytwo[user]["numBets"] -= 1
                                copytwo[user]["totalWagered"] -= round(added_wagers[i])
                                copytwo[user]["balance"] += round(added_wagers[i])
                                if int(added_oddsB[i]) < 0:
                                    copytwo[user]["overWagered"] -= int(added_oddsB[i])
                                else:
                                    copytwo[user]["underWagered"] -= int(added_oddsB[i])

                        copytwo[user]["returnRate"] = round(float(copytwo[user]["totalWon"]) / float(copytwo[user]["totalWagered"]), 2) * 100
                        copytwo[user]["winrate"] = round(float(copytwo[user]["wonBets"]) / float(copytwo[user]["numBets"]), 2) * 100


                        if len(userscopy[user]["bets"]["events"][prev_event][fighter]) == 2 + fighter.count('+'):
                            del userscopy[user]["bets"]["events"][prev_event][fighter]
                            await ctx.send(embed = em)
                            continue

                        while len(userscopy[user]["bets"]["events"][prev_event][fighter].keys()) != 0:
                            delindex = list(userscopy[user]["bets"]["events"][prev_event][fighter].keys())[0]
                            del userscopy[user]["bets"]["events"][prev_event][fighter][delindex]

                        if len(userscopy[user]["bets"]["events"][prev_event][fighter]) == 0:
                            del userscopy[user]["bets"]["events"][prev_event][fighter]

                        await ctx.send(embed = em)
                        continue


                    for odds in users[user]["bets"]["events"][prev_event][fighter]:
                        bet = users[user]["bets"]["events"][prev_event][fighter][odds]
                        decimal = oddsToDecimal(int(odds))
                        em = discord.Embed(title = f"{await client.fetch_user(int(user))}'s bet result")
                        em.add_field(name="Fighter", value = fighter)

                        if fighter in ufcwinner:
                            em.add_field(name = "Bet Result", value = "Won")
                            em.add_field(name = "Odds Taken", value = odds)
                            em.add_field(name = "Wagered", value = bet)
                            em.add_field(name = "Payout", value = round(bet * decimal))
                            em.add_field(name = "Profit/Loss", value = round((bet * decimal) - bet))
                            copytwo[user]["wonBets"] += 1
                            copytwo[user]["totalWon"] += round(bet * decimal)
                            copytwo[user]["balance"] += round(bet * decimal)

                        elif fighter in ufcloser:
                            em.add_field(name = "Bet Result", value = "Lost")
                            em.add_field(name = "Odds Taken", value = odds)
                            em.add_field(name = "Wagered", value = bet)
                            em.add_field(name = "Payout", value = 0)
                            em.add_field(name = "Profit/Loss", value = -abs(bet))

                        else:
                            em.add_field(name = "Bet Result", value = "Cancelled")
                            em.add_field(name = "Odds Taken", value = odds)
                            em.add_field(name = "Wagered", value = bet)
                            em.add_field(name = "Payout", value = bet)
                            em.add_field(name = "Profit/Loss", value = 0)
                            copytwo[user]["totalWagered"] -= bet
                            copytwo[user]["numBets"] -= 1
                            if int(odds) < 0:
                                copytwo[user]["overWagered"] -= bet
                            else:
                                copytwo[user]["underWagered"] -= bet

                        copytwo[user]["returnRate"] = round(float(copytwo[user]["totalWon"]) / float(copytwo[user]["totalWagered"]), 2) * 100
                        copytwo[user]["winrate"] = round(float(copytwo[user]["wonBets"]) / float(copytwo[user]["numBets"]), 2) * 100

                        if len(userscopy[user]["bets"]["events"][prev_event][fighter]) == 1:
                            del userscopy[user]["bets"]["events"][prev_event][fighter]
                            await ctx.send(embed = em)
                            continue

                        del userscopy[user]["bets"]["events"][prev_event][fighter][odds]
                        await ctx.send(embed = em)
                    
                for event in userscopy[user]["bets"]["events"].keys():
                    if len(userscopy[user]["bets"]["events"][event]) == 0:
                        del copytwo[user]["bets"]["events"][event]
            with open("storedbets.json", "w") as f:
                json.dump(copytwo, f)
        else:
            return

                

    async def open_account(user):
        users = await get_user_stats()
        if str(user.id) in users:
            nothing = 0
        else:
            newaccount = {
                str(user.id):{
                    "balance": 1000,
                    "left": 0,
                    "right": 0,
                    "numBets": 0,
                    "wonBets": 0,
                    "winrate": 0,
                    "totalWagered": 0,
                    "totalWon": 0,
                    "returnRate": 0,
                    "totalOdds": 0,
                    "overOdds": 0,
                    "overWagered": 0,
                    "underOdds": 0,
                    "underWagered": 0,
                    "bets": {
                        "events" : {

                        }
                    }

            }}
            users.update(newaccount)
        with open("storedbets.json", "w") as f:
            json.dump(users,f)
        return True

    async def get_user_stats():
        with open("storedbets.json", "r") as f:
            users = json.load(f)
        return users

    def get_all_keys(d):
        for key, value in d.items():
            yield key
            if isinstance(value, dict):
                yield from get_all_keys(value)

    async def results():
        global prev_event, ufcwinner, ufcloser
        ufcwinner = []
        ufcloser = []
        prev_event = ""
        users = await get_user_stats()

        for x in get_all_keys(users):
            if x.find('UFC') != -1:
                prev_event = x


        searchTerm = prev_event.replace(' ','+')
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            page = requests.get("https://www.tapology.com/search?term="+searchTerm+"&commit=Submit&model%5Bevents%5D=eventsSearch", headers=headers)
            soup = BeautifulSoup(page.content, 'html.parser')
        except:

            return
        try:  
            eventFound = soup.find('table', class_="fcLeaderboard").find('td').find('a')
        except:
            searchTerm = searchTerm.replace("ON+ESPN", "FIGHT+NIGHT")
            try:
                page = requests.get("https://www.tapology.com/search?term="+searchTerm+"&commit=Submit&model%5Bevents%5D=eventsSearch", headers=headers)
                soup = BeautifulSoup(page.content, 'html.parser')
            except:

                return
            try:  
                eventFound = soup.find('table', class_="fcLeaderboard").find('td').find('a')
            except:

                return
        try:    
            page = requests.get("https://www.tapology.com"+eventFound['href'], headers=headers)
            soup = BeautifulSoup(page.content, 'html.parser')
        except:

            return
        try:        
            fightCard = soup.find('h3', text="Fight Card").findNext('ul').findAll('li')
        except:

            return
        
        output = "__"+eventFound.text+" Results__\n"
    
        for fight in fightCard:
            result = fight.find(class_="result")
            if not (result):
                result = "NONE"
            else:
                result = result.text.strip()
                result = result.split(',')[0]+"("+result.split(', ')[1]+")"
            
            fighterLeft = fight.find(class_="fightCardFighterName left")
            if not (fighterLeft):
                break
            fighterLeft = fighterLeft.text.strip()
            
            fighterRight = fight.find(class_="fightCardFighterName right")
            if not (fighterRight):
                break
            fighterRight = fighterRight.text.strip()
            
            time = fight.find(class_="time")
            if not(time):
                time = " "
            else:
                time = time.text.strip()
                
            if(result == "NONE"):
                output += (fighterLeft+" vs. "+fighterRight+"\n")
            elif(result.find("Draw") >= 0 or result.find("No Contest") >= 0):
                output += (fighterLeft+" vs. "+fighterRight+" "+result+"\n")
            elif(result.find("Decision") >= 0):
                output += (fighterLeft+" defeated "+fighterRight+" via "+result+"\n")
            else:
                time = time.split(' ')
                output += (fighterLeft+" defeated "+fighterRight+" via "+result+" at "+time[0]+" of "+time[1]+" "+time[2] +"\n")
            ufcwinner.append(simplify(fighterLeft))
            ufcloser.append(simplify(fighterRight))
        global ufclist
        ufclist = output.split('\n')
        # fighterleft = winner
        # fighterright = loser

    @tasks.loop(seconds = 5)
    async def updatetwitchbet(initial, left, right):
        try:
            global is_active, embed_dict, seconds
            users = await get_user_stats()
            totalleft = 0
            totalright = 0
            total = 0
            for user in users.keys():
                totalleft += users[user]["left"]
                totalright += users[user]["right"]
                total = totalleft + totalright
            seconds -= 5
            for field in embed_dict["fields"]:
                if field['name'] == "Time remaining":
                    if seconds <= 0:
                        field["value"] = "Bets Closed"
                    else:
                        field["value"] = int(field["value"])
                        field["value"] -= 5
                if field['name'] == left:
                    field["value"] = totalleft
                if field['name'] == right:
                    field['value'] = totalright
                if field['name'] == 'left side payout':
                    if total > 0 and totalleft > 0:
                        field['value'] = str(round((1 / (totalleft / total)), 2))
                if field['name'] == 'right side payout':
                    if total > 0 and totalright > 0:
                        field['value'] = str(round((1 / (totalright / total)), 2))

            embed = discord.Embed.from_dict(embed_dict)
            await initial.edit(embed = embed)
            if seconds <= 0:
                is_active = 2
                updatetwitchbet.stop()
            else:
                is_active = 1
        except Exception as e:
            print(e)

        

    @client.command()
    async def custombet(ctx, time: int, *, title):
        """Creates custom bet (!createbet {seconds active} {title of bet})"""
        global is_active
        if is_active == 1:
            await ctx.send("There is already a bet active")
            return
        elif is_active == 2:
            await ctx.send("There is an unresolved bet")
            return
        is_active = 1
        global seconds
        seconds = int(time)
        em = discord.Embed(title = title)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        await ctx.send("What is the left side bet")
        msg = await client.wait_for("message", check = check)
        left = msg.content
        await ctx.send("What is the right side bet")
        msg = await client.wait_for("message", check=check)
        right = msg.content
        em.add_field(name = left, value = 0)
        em.add_field(name = right, value = 0)
        em.add_field(name = "left side payout", value = 0)
        em.add_field(name = "right side payout", value = 0)
        em.add_field(name = "Time remaining", value = int(time))
        initial = await ctx.send(embed = em)
        global embed_dict
        embed_dict = em.to_dict()
        await asyncio.sleep(5)
        updatetwitchbet.start(initial, left, right)
        """while is_active != 0:
            embed_dict, seconds = await updatetwitchbet(initial, embed_dict, seconds)"""
        
            
    @client.command()
    async def left(ctx, amount: int):
        """Bets on left side of created bet (!left {wager amount})"""
        global is_active
        if is_active != 1:
            await ctx.send("Bet is not open.")
            return
        if amount <= 0:
            await ctx.send("Cannot bet less than 1.")
            return
        users = await get_user_stats()
        for user in users.keys():
            if user == str(ctx.author.id):
                if amount > users[user]["balance"]:
                    await ctx.send("You cannot wager more than your balance.")
                    return
                users[user]["left"] += amount
                users[user]["balance"] -= amount
        with open("storedbets.json", "w") as f:
            json.dump(users, f)

    @client.command()
    async def right(ctx, amount: int):
        """Bets on right side of created bet (!right {wager amount})"""
        global is_active
        if is_active != 1:
            await ctx.send("Bet is not open.")
            return
        if amount <= 0:
            await ctx.send("Cannot bet less than 1.")
            return
        users = await get_user_stats()
        for user in users.keys():
            if user == str(ctx.author.id):
                if amount > users[user]["balance"]:
                    await ctx.send("You cannot wager more than your balance.")
                    return
                users[user]["right"] += amount
                users[user]["balance"] -= amount
        with open("storedbets.json", "w") as f:
            json.dump(users, f)

    @client.command()
    async def resolve(ctx, result):
        """Resolves created bet (!resolve {left, right, cancel})"""
        global is_active
        if is_active == 0:
            await ctx.send("There is no active bet to resolve")
            return
        result = result.lower()
        totalleft = 0
        totalright = 0
        users = await get_user_stats()
        for user in users.keys():
            totalleft += users[user]["left"]
            totalright += users[user]["right"]
            total = totalleft + totalright
        for user in users.keys():
            if result == "left":
                if is_active == 1:
                    await ctx.send("Cannot resolve ongoing bet")
                    return
                left = users[user]["left"]
                users[user]["balance"] += round((1 / (totalleft / total)), 2) * left
                users[user]["left"] = 0
                users[user]["right"] = 0
                if left != 0:
                    await ctx.send(f'{round((1 / (totalleft / total)), 2) * left} paid out to @{await client.fetch_user(int(user))}')
            elif result == "right":
                if is_active == 1:
                    await ctx.send("Cannot resolve ongoing bet")
                    return
                right = users[user]["right"]
                users[user]["balance"] += round((1 / (totalright / total)), 2) * right
                users[user]["left"] = 0
                users[user]["right"] = 0
                if right != 0:
                    await ctx.send(f'{round((1 / (totalright / total)), 2) * right} paid out to @{await client.fetch_user(int(user))}')
            elif result == "cancel" or totalleft == 0 or totalright == 0:
                left = users[user]["left"]
                right = users[user]["right"]
                leftright = left + right
                users[user]["balance"] += left
                users[user]["balance"] += right
                users[user]["left"] = 0
                users[user]["right"] = 0
                if leftright != 0:
                    await ctx.send(f'{leftright} returned to @{await client.fetch_user(int(user))}')
            else:
                await ctx.send("Invalid parameter")
                return
        with open("storedbets.json", "w") as f:
            json.dump(users, f)
        is_active = 0

    @client.command()
    async def ufcpast(ctx):
        """Prints results of past ufc event."""
        await ctx.send("\n".join(ufclist))
        return

    @client.command()
    async def winners(ctx):
        await ctx.send(ufcwinner)

    @client.command()
    async def losers(ctx):
        await ctx.send(ufcloser)

    @client.command()
    async def manualbetpayout(ctx):
        await payoutUFC()
        return

    @client.command()
    async def convert(ctx, arg):
        "Converts American odds to decimal odds and vice versa (Format: '!convert +300' or '!convert 2.5x')."
        if arg.find("x") != -1 or arg.find("X") != -1:
            if float(arg[:-1]) >= 2:
                await ctx.send(f"+{round((float(arg[:-1]) - 1) * 100)}")
                return
            else:
                await ctx.send(round(-100 / (float(arg[:-1]) - 1)))
                return
        else:
            if int(arg) >= 100:
                await ctx.send(f"{round(((int(arg) / 100) + 1), 2)}x")
                return
            else:
                await ctx.send(f"{round(((100 / abs(int(arg))) + 1), 2)}x")
                return

    @client.command()
    async def ufcbet(ctx, index, amount):
        "Adds a bet to the ufc (Format: '!ufcbet [index] [your_bet_amount]'). For parlays the indices must be separated by +. (Format: '!ufcbet 1+4+21 250). Index can be found using !ufc. Just use integers for your bets."

        users = await get_user_stats()

        if int(amount) < 1:
            await ctx.send("You cannot bet less than 1.")
            return

        if users[str(ctx.author.id)]["balance"] < 1:
            await ctx.send("You have no money.")
            return
        if users[str(ctx.author.id)]["balance"] < int(amount):
            await ctx.send("You cannot bet more than your balance.")
            return

        if index.find("+") != -1:
            indexlist = index.split('+')
            fighter_odds_list = []
            splitindexlist = []
            fighterlist = []
            oddslist = []
            fighterstring = ""
            oddsstring = ""
            for fight in indexlist:
                if int(fight) > len(ufctable) or int(fight) < 1:
                    await ctx.send(f"Fight {fight} does not exist.")
                    return
            for index in indexlist:
                fighter_odds_list.append(ufctable[int(index) - 1])
            for fightplusodds in fighter_odds_list:
                if fightplusodds.find("+") != -1:
                    splitindexlist.append(fightplusodds.find("+"))
                else:
                    splitindexlist.append(fightplusodds.find("-"))

            for index in range(len(fighter_odds_list)):
                fighterlist.append(fighter_odds_list[index][:splitindexlist[index] - 1])
                oddslist.append(fighter_odds_list[index][splitindexlist[index]:])
                fighterstring += f"{fighter_odds_list[index][:splitindexlist[index] - 1]}+"
                oddsstring += f"{fighter_odds_list[index][splitindexlist[index]:]}+"

            fighterstring = fighterstring[:-1]
            oddsstring = oddsstring[:-1]
            totaldecimal = 1
            totalodds = 0


            for odds in oddslist:
                decimal = oddsToDecimal(int(odds))
                totaldecimal = totaldecimal * decimal

            if totaldecimal >= 2:
                totalodds = (totaldecimal - 1) * 100
            else:
                totalodds = -100 /  (totaldecimal - 1)

            if ufcevent in users[str(ctx.author.id)]["bets"]["events"]:
                if fighterstring in users[str(ctx.author.id)]["bets"]["events"][ufcevent]:
                    if totalodds in users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighterstring]:
                        users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighterstring][int(totalodds)] += int(amount)
                    else:
                        users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighterstring].update({int(totalodds): int(amount)})
                        for x in range(len(oddslist)):
                            users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighterstring].update({fighterlist[x]: oddslist[x]})
                else:
                    users[str(ctx.author.id)]["bets"]["events"][ufcevent].update({fighterstring:{int(totalodds) : int(amount)}})
                    for x in range(len(oddslist)):
                        users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighterstring].update({fighterlist[x]: oddslist[x]})
            else:
                users[str(ctx.author.id)]["bets"]["events"].update({ufcevent:{fighterstring:{int(totalodds) : int(amount)}}})
                for x in range(len(oddslist)):
                    users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighterstring].update({fighterlist[x]: oddslist[x]})

            users[str(ctx.author.id)]["numBets"] += 1
            users[str(ctx.author.id)]["totalWagered"] += int(amount)
            users[str(ctx.author.id)]["totalOdds"] += (int(totalodds))
            users[str(ctx.author.id)]["balance"] -= int(amount)
            # overdog is -
            # underdog is +
            if int(totalodds) < 0:
                users[str(ctx.author.id)]["overWagered"] += int(amount)
                users[str(ctx.author.id)]["overOdds"] = ((int(amount)/users[str(ctx.author.id)]["overWagered"] * int(totalodds)) + ((1 - int(amount)/users[str(ctx.author.id)]["overWagered"]) * users[str(ctx.author.id)]["overOdds"]))
            else:
                users[str(ctx.author.id)]["underWagered"] += int(amount)
                users[str(ctx.author.id)]["underOdds"] = ((int(amount)/users[str(ctx.author.id)]["underWagered"] * int(totalodds)) + ((1 - int(amount)/users[str(ctx.author.id)]["underWagered"]) * users[str(ctx.author.id)]["underOdds"]))
            with open("storedbets.json", "w") as f:
                json.dump(users, f)

            em = discord.Embed(title = "Bet Placed!")
            em.add_field(name = "User", value = ctx.message.author)
            em.add_field(name = "Wager", value = amount)
            em.add_field(name = "Odds", value = int(totalodds))
            em.add_field(name = "Fighter", value = fighterstring)

            await ctx.send(embed = em)
            return

        else:

            if int(index) > len(ufctable) or int(index) < 1:
                await ctx.send("Fight does not exist.")
                return
            
            splitindex = 0
            fighter_odds = ufctable[int(index) - 1]
            if fighter_odds.find("+") != -1:
                splitindex = fighter_odds.find("+")
            else:
                splitindex = fighter_odds.find("-")
            fighter = fighter_odds[:splitindex - 1]
            odds = fighter_odds[splitindex:]

            if ufcevent in users[str(ctx.author.id)]["bets"]["events"]:
                if fighter in users[str(ctx.author.id)]["bets"]["events"][ufcevent]:
                    if odds in users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighter]:
                        users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighter][odds] += int(amount)
                    else:
                        users[str(ctx.author.id)]["bets"]["events"][ufcevent][fighter].update({odds : int(amount)})
                else:
                    users[str(ctx.author.id)]["bets"]["events"][ufcevent].update({fighter:{odds : int(amount)}})
            else:
                users[str(ctx.author.id)]["bets"]["events"].update({ufcevent:{fighter:{odds : int(amount)}}})
            
            users[str(ctx.author.id)]["numBets"] += 1
            users[str(ctx.author.id)]["totalWagered"] += int(amount)
            users[str(ctx.author.id)]["totalOdds"] += (int(odds))
            users[str(ctx.author.id)]["balance"] -= int(amount)
            # overdog is -
            # underdog is +
            if int(odds) < 0:
                users[str(ctx.author.id)]["overWagered"] += int(amount)
                users[str(ctx.author.id)]["overOdds"] = ((int(amount)/users[str(ctx.author.id)]["overWagered"] * int(odds)) + ((1 - int(amount)/users[str(ctx.author.id)]["overWagered"]) * users[str(ctx.author.id)]["overOdds"]))
            else:
                users[str(ctx.author.id)]["underWagered"] += int(amount)
                users[str(ctx.author.id)]["underOdds"] = ((int(amount)/users[str(ctx.author.id)]["underWagered"] * int(odds)) + ((1 - int(amount)/users[str(ctx.author.id)]["underWagered"]) * users[str(ctx.author.id)]["underOdds"]))
            with open("storedbets.json", "w") as f:
                json.dump(users, f)

            em = discord.Embed(title = "Bet Placed!")
            em.add_field(name = "User", value = ctx.message.author)
            em.add_field(name = "Wager",value = amount)
            em.add_field(name = "Odds", value =  odds)
            em.add_field(name = "Fighter", value = fighter)

            await ctx.send(embed = em)

    @client.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You must enter all parameters.")

    client.loop.create_task(updateUFC())
    client.run(os.getenv("TOKEN"))



if __name__ == '__main__':
    main()

