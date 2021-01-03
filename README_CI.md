# About RENAT CI tests


RENAT CI test cases have been implemented by a Github action which is triggerd automatically when a push or pull-request to master branch happens.

## Overall
RENAT test cases run insides a RENAT container (based on dockerhub bachng/renat_base7 image and the commited RENAT source code)

There are 2 type of test cases:
  1. Shell test case: for testing RENAT shell scripts
  2. RENAT test case: for testing RENAT items

The default network topology used for RENAT test cased is a simple network including 2 quagga container connected directly ( Future work will include more sophisticated network topoligy).

The topology and related nodes are described in `.test/docker-compose.yaml`

```
+-------- +                                                         +---------+
| R1      +--eth0(192.168.0.101/24) --BGP-- (192.168.0.102/24)eth0--+ R2      |
| AS65001 |                          OSPF                           | AS65001 |
+---------+                                                         +---------+

renat_server: 192.168.0.100/24
```

## How to add more test cases
- For shell test case, add more folder with a `run.sh` under `.test/test_shell` folder. Every `run.sh` in sub folders will be executed by the running script.
- For RENAT test case, add more item under the only one project `.test/test_renat` as usual. Check README.md for more detail about how to write RENAT items.

`run_test.sh` is the runnin script to used by docker-compose to run the tests which is executed automatically by Github action.

In local environment, tests could be run with docker-compose environment by:
```
cd $RENAT_PATH/.test
docker-compose up --exit-code-from test_renat
```
