import datetime


def reminder_text(invoice, today=None):
    if today == None:
        today = datetime.date.today()
    days = (today - invoice["due"]).days
    if days > 0:
        if days > 30:
            if invoice["lang"] == "nl":
                txt = "Beste " + invoice["name"] + ", uw factuur " + str(invoice["number"]) + " is " + str(days) + " dagen te laat. Dit is een laatste herinnering."
            else:
                txt = "Dear " + invoice["name"] + ", your invoice " + str(invoice["number"]) + " is " + str(days) + " days overdue. This is a final reminder."
        else:
            if invoice["lang"] == "nl":
                txt = "Beste " + invoice["name"] + ", uw factuur " + str(invoice["number"]) + " is " + str(days) + " dagen te laat."
            else:
                txt = "Dear " + invoice["name"] + ", your invoice " + str(invoice["number"]) + " is " + str(days) + " days overdue."
        return txt
    else:
        return None


def reminders_for(invoices, today=None):
    result = []
    for i in range(len(invoices)):
        t = reminder_text(invoices[i], today)
        if t != None:
            result.append(t)
    return result
