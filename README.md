# energycare_addons

MRP Team:
========================
Create/Edit:
Manufacturing > Configuration > Manufacturing Team

Configure on:
Manufacturing > Master Data > Work Centers

Note: if MRP Team is undefined in workcenter then it will be used by any team user.


Create Finish SN From Component SN:
========================
Make field `Create Finish SN From Component SN` enable to create/assign finish SN from component SN, basically used in first sequential workorder.

if true: Scan the Component SN and assign it to Finish SN on `Validate`

if false: Scan Finish SN and then scan Component SN and assign the Component SN to Finish SN on `Validate`.


Unbuild product flow during the manufacturing process:
===============================
Add product for unbuild('disassemble') form Rework Station work-order.

First user send a product to rework station and after that rework station user will be able to unbuild it and the component will available to reprocess of build that product.
