#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

reward="0.0"
set +e
bash /opt/bootstrap/start_stack.sh > /logs/verifier/bootstrap.log 2>&1
bootstrap_status=$?

reseed_status=99
outputs_status=99
guardrails_status=99
mutation_status=99

if [ "$bootstrap_status" -eq 0 ]; then
  php /app/workspace/scripts/reseed.php > /logs/verifier/reseed.log 2>&1
  reseed_status=$?
fi

if [ "$reseed_status" -eq 0 ]; then
  python3 /tests/test_outputs.py > /logs/verifier/test_outputs.log 2>&1
  outputs_status=$?
fi

if [ "$outputs_status" -eq 0 ]; then
  python3 /tests/test_guardrails.py > /logs/verifier/test_guardrails.log 2>&1
  guardrails_status=$?
fi

if [ "$guardrails_status" -eq 0 ]; then
  python3 /tests/test_mutation.py > /logs/verifier/test_mutation.log 2>&1
  mutation_status=$?
fi
set -e

if [ "$bootstrap_status" -eq 0 ] \
  && [ "$reseed_status" -eq 0 ] \
  && [ "$outputs_status" -eq 0 ] \
  && [ "$guardrails_status" -eq 0 ] \
  && [ "$mutation_status" -eq 0 ]; then
  reward="1.0"
fi

printf '%s\n' "$reward" > /logs/verifier/reward.txt
{
  echo "bootstrap_status=$bootstrap_status"
  echo "reseed_status=$reseed_status"
  echo "test_outputs_status=$outputs_status"
  echo "test_guardrails_status=$guardrails_status"
  echo "test_mutation_status=$mutation_status"
} > /logs/verifier/status.txt

for log_file in /logs/verifier/status.txt /logs/verifier/bootstrap.log /logs/verifier/reseed.log /logs/verifier/test_outputs.log /logs/verifier/test_guardrails.log /logs/verifier/test_mutation.log; do
  if [ -f "$log_file" ]; then
    printf '===== %s =====\n' "$(basename "$log_file")" >> /logs/verifier/test-stdout.txt
    cat "$log_file" >> /logs/verifier/test-stdout.txt
    printf '\n' >> /logs/verifier/test-stdout.txt
  fi
done

[ "$reward" = "1.0" ]
