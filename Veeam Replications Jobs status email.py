# Step 1: SMTP Configuration
$SMTPServer = "your_smtp_server"
$SMTPPort = 587  
$SMTPUser = "your_email@example.com"
$SMTPPass = "your_email_password"
$FromEmail = "your_email@example.com"
$ToEmail = "recipient@example.com"

# Step 2: Get Today's Date
$today = (Get-Date).Date

# Step 3: Retrieve All Replication Jobs
Write-Host "Fetching replication jobs from Veeam..."
$jobs = Get-VBRJob | Where-Object { $_.JobType -eq "Replica" }
Write-Host "Total replication jobs found: $($jobs.Count)"

# Step 4: Initialize an empty list to store job results
$result = @()
$counter = 0  

# Step 5: Loop Through Each Replication Job
foreach ($job in $jobs) {
    $counter++
    Write-Progress -Activity "Processing Replication Jobs" -Status "Checking job: $($job.Name)" -PercentComplete (($counter / $jobs.Count) * 100)

    # Get today's successful session
    $session = Get-VBRBackupSession | Where-Object { 
        $_.JobId -eq $job.Id -and $_.Result -eq "Success" -and $_.EndTime.Date -eq $today
    } | Select-Object -First 1  

    # If no session was found today, get the last successful session
    if (-not $session) {
        $session = Get-VBRBackupSession | Where-Object { 
            $_.JobId -eq $job.Id -and $_.Result -eq "Success"
        } | Sort-Object EndTime -Descending | Select-Object -First 1  
    }

    # Determine completion status and status message
    if ($session) {
        $completionTime = $session.EndTime
        if ($completionTime.Date -eq $today) { 
            $status = "<span style='color:green; font-weight:bold;'>✅ Completed</span>" 
        } else { 
            $status = "<span style='color:red; font-weight:bold;'>❌ Pending</span>" 
        }
        Write-Host "[✔] Job '$($job.Name)' last completed at $completionTime ($status)"
    } else {
        $completionTime = "Never Completed Successfully"
        $status = "<span style='color:red; font-weight:bold;'>❌ Never Completed</span>"
        Write-Host "[✘] No successful session found for '$($job.Name)'."
    }

    # Store job details
    $result += [PSCustomObject]@{
        JobName = $job.Name
        CompletionTime = $completionTime
        Status = $status
    }
}

# Step 6: Check if any jobs exist
if ($result.Count -eq 0) {
    Write-Host "No replication jobs found."
    exit
}

# Step 7: Generate an HTML Table for Email with Colored Status
Write-Host "Generating email report..."
$HTML = @"
<html>
<head>
    <style>
        table {border-collapse: collapse; width: 100%;}
        th, td {border: 1px solid black; padding: 8px; text-align: left;}
        th {background-color: #f2f2f2;}
    </style>
</head>
<body>
    <h2>Veeam Replication Job Report - $(Get-Date -Format "yyyy-MM-dd")</h2>
    <table>
        <tr>
            <th>Project Name</th>
            <th>Last Successful Completion Time</th>
            <th>Status</th>
        </tr>
"@

foreach ($job in $result) {
    $HTML += "<tr><td>$($job.JobName)</td><td>$($job.CompletionTime)</td><td>$($job.Status)</td></tr>"
}

$HTML += @"
    </table>
</body>
</html>
"@

# Step 8: Configure SMTP Client to Send Email
Write-Host "Preparing email for sending..."
$SMTPClient = New-Object System.Net.Mail.SmtpClient($SMTPServer, $SMTPPort)
$SMTPClient.Credentials = New-Object System.Net.NetworkCredential($SMTPUser, $SMTPPass)
$SMTPClient.EnableSsl = $true  

# Step 9: Create Email Message
$MailMessage = New-Object System.Net.Mail.MailMessage
$MailMessage.From = $FromEmail
$MailMessage.To.Add($ToEmail)
$MailMessage.Subject = "Veeam Replication Job Report - $(Get-Date -Format 'yyyy-MM-dd')"
$MailMessage.IsBodyHtml = $true
$MailMessage.Body = $HTML

# Step 10: Send Email and Handle Errors
try {
    Write-Host "Sending email..."
    $SMTPClient.Send($MailMessage)
    Write-Host "✅ Email sent successfully!"
} catch {
    Write-Host "❌ Error sending email: $_"
}
