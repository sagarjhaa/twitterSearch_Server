Sub SendMessage(DisplayMsg,Message)
          Dim objOutlook 'As Outlook.Application
          Dim objOutlookMsg 'As Outlook.MailItem
          Dim objOutlookRecip 'As Outlook.Recipient
          Dim objOutlookAttach 'As Outlook.Attachment

          ' Create the Outlook session.
          Set objOutlook = CreateObject("Outlook.Application")

          ' Create the message.
          'Set objOutlookMsg = objOutlook.CreateItem(olMailItem)
          Set objOutlookMsg = objOutlook.CreateItem(0)

        timestamp = Now()

          With objOutlookMsg

              .To = "Sagar Jha Gmail"
              .CC = "Xinyue Ye"

             ' Set the Subject, Body, and Importance of the message.
             .Subject = Message

             '.Body = "This is the body of the message." & vbCrLf & vbCrLf
             .Body = "Execute server run successfully.Date Time Stamp: " & timestamp

             '.Importance = olImportanceHigh  'High importance

             ' Add attachments to the message.
             'If Not IsMissing(AttachmentPath) Then
             'Set objOutlookAttach = .Attachments.Add(AttachmentPath)
             'End If

             ' Resolve each Recipient's name.
             For Each objOutlookRecip In .Recipients
                 objOutlookRecip.Resolve
             Next

             ' Should we display the message before sending?
             If DisplayMsg Then
                 .Display
             Else
                 .Save
                 .Send
             End If
          End With
          Set objOutlook = Nothing
End Sub

call SendMessage (False,"Server Process has ended")