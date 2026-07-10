# CI permission investigation

1. Identify the job, event trigger, and exact API operation that received the authorization error.
2. Compare the workflow's declared permissions with the minimum permission required by that operation.
3. Check whether repository or organization policy constrains the workflow token.
4. Propose the smallest reviewable workflow permission change; do not alter permissions directly.
