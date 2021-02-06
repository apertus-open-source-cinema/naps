# additional notes

* formal check for stream contract
    * valid not depends on ready
    * no combinatorial dependency
* syntactic conventions for streams (input as constructor argument seems suboptimal)
* On master and slave interfaces there must be no combinatorial paths between input and output signals. <- this rule is shit