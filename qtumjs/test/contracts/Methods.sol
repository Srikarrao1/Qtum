pragma solidity ^0.4.24;

contract Methods {

  uint256 foo;

  function setFoo(uint256 _foo) public {
    foo = _foo;
  }

  function getFoo() public view returns(uint256) {
    return foo;
  }
}
