# ERC20 Integration Notes

- ERC-20 defines `transfer` and `transferFrom`, and callers are expected to handle a returned `false` value.
- The standard also notes the long-known allowance overwrite race and points integrators toward zero-first approval flows in user interfaces.
- Metadata helpers such as `name`, `symbol`, and `decimals` are common but not mandatory in the base standard.
