## Date : 02-24-2015
## Change : Included the csv module and removed the use of pandas
## Developer : Sagar Jha
## Update : Dialogbox to ask for file , Dt: 02-25-2015

import nltk  #install nltk inadvance
from nltk import FreqDist
import csv
from tkinter import Tk
from tkinter.filedialog import askopenfilename 

#Constants and Initilization
col_list = [17]  #The column number needs to be fetched
 #Number of total rows
data = []  
tw =[]

#Open File and create list of the target column
#read "tweet_text" column data


def choosefile():
    root = Tk()
    root.withdraw()
    filename = askopenfilename()
    root.destroy()
    return filename

##filename = "C:\\Users\\sjha1\\Desktop\\Sagar_Docs\\Special v7\\v7_4\\Ksu_Test\\KSU.csv"

def fileprocess(filename,tags):
    row_count = 0
    if filename != "":
        with open(filename,encoding="latin-1") as fp:    #"C:\\Users\\sjha1\\Desktop\\KSU.csv","r"
            reader = csv.reader(fp)
            for rows in reader:
                row_count = row_count + 1
                data.append(list(rows[i+1] for i in col_list))

        #Reformat the list to expected format
        for i in range(row_count):
            temp_list = ','.join(data[i])
            tw.append(temp_list)

        # get the list of words from all the sentences
        wlist = []
        for item in tw:
            words = item.split(" ")
            for word in words:
                wlist.append(word)

        #convet it to nltk.Text format
        text = nltk.Text(wlist)

        #fdist1 = FreqDist(text)
        ##["Kent","Shooting"]
        tags_list = tags.split(",")
        text.dispersion_plot(tags_list)
        return

##abc = choosefile()
##tags = "big"
##fileprocess(abc,tags)


    
