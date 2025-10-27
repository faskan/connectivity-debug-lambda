## Test the lambda

aws lambda invoke \
--function-name debug-lambda \
--cli-binary-format raw-in-base64-out \
--payload file://test/payload.json \
out.json