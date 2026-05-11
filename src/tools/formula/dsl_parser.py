"""
Proper DSL parser for strategy formulas.

This parser understands the DSL syntax natively and evaluates it correctly
without regex replacements or operator conversions.

Supported syntax:
  - indicator[shift]: sha_10_green[0], ema_20[-1], adx_14[-2]
  - Comparisons: ==, !=, <, >, <=, >=
  - Logical: && (and), || (or), ! (not)
  - Parentheses for grouping
  - Arithmetic: +, -, *, /

Examples:
  sha_10_green[-1] && sha_10_red[-2] == 1 && ema_20 < close && adx_14 > adx_14[-1]
  (rsi_14 > 50) || (macd_12_26 > 0)
  !(close > sma_200)
"""

import re
from typing import Union, Any, List, Tuple
import pandas as pd


class Token:
    """Represents a lexical token."""
    
    def __init__(self, type_: str, value: str):
        self.type = type_
        self.value = value
    
    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


class Lexer:
    """Tokenizes DSL formula strings."""
    
    # Token patterns (order matters - more specific patterns first)
    TOKEN_PATTERNS = [
        ('NUMBER', r'\d+\.?\d*'),
        ('INDICATOR', r'([a-z_][a-z0-9_]*)\[(-?\d+)\]'),  # indicator[shift]
        ('AND', r'&&|and\b'),  # Support both && and 'and'
        ('OR', r'\|\||or\b'),   # Support both || and 'or'
        ('NOT', r'!|not\b'),    # Support both ! and 'not'
        ('NAME', r'[a-z_][a-z0-9_]*'),  # variable names
        ('LPAREN', r'\('),
        ('RPAREN', r'\)'),
        ('LBRACKET', r'\['),
        ('RBRACKET', r'\]'),
        ('EQ', r'=='),
        ('NE', r'!='),
        ('LE', r'<='),
        ('GE', r'>='),
        ('LT', r'<'),
        ('GT', r'>'),
        ('PLUS', r'\+'),
        ('MINUS', r'-'),
        ('MUL', r'\*'),
        ('DIV', r'/'),
        ('WS', r'\s+'),
    ]
    
    def __init__(self, formula: str):
        self.formula = formula
        self.tokens: List[Token] = []
        self.tokenize()
    
    def tokenize(self):
        """Break formula into tokens."""
        pos = 0
        while pos < len(self.formula):
            matched = False
            
            for token_type, pattern in self.TOKEN_PATTERNS:
                regex = re.match(pattern, self.formula[pos:])
                if regex:
                    value = regex.group(0)
                    if token_type != 'WS':  # Skip whitespace
                        self.tokens.append(Token(token_type, value))
                    pos += len(value)
                    matched = True
                    break
            
            if not matched:
                raise SyntaxError(f"Unexpected character at position {pos}: {self.formula[pos]}")
    
    def get_tokens(self) -> List[Token]:
        return self.tokens


class Parser:
    """Parses tokenized formula into AST."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def current_token(self) -> Token:
        """Get current token without consuming."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def consume(self, expected_type: str = None) -> Token:
        """Consume and return current token."""
        token = self.current_token()
        if token is None:
            raise SyntaxError("Unexpected end of formula")
        if expected_type and token.type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {token.type}")
        self.pos += 1
        return token
    
    def parse(self) -> 'ASTNode':
        """Parse formula into AST."""
        ast = self.parse_or()
        if self.current_token() is not None:
            raise SyntaxError(f"Unexpected token: {self.current_token()}")
        return ast
    
    def parse_or(self) -> 'ASTNode':
        """Parse logical OR (lowest precedence)."""
        left = self.parse_and()
        while self.current_token() and self.current_token().type == 'OR':
            self.consume('OR')
            right = self.parse_and()
            left = BinaryOp('||', left, right)
        return left
    
    def parse_and(self) -> 'ASTNode':
        """Parse logical AND."""
        left = self.parse_comparison()
        while self.current_token() and self.current_token().type == 'AND':
            self.consume('AND')
            right = self.parse_comparison()
            left = BinaryOp('&&', left, right)
        return left
    
    def parse_comparison(self) -> 'ASTNode':
        """Parse comparison operations."""
        left = self.parse_additive()
        
        token = self.current_token()
        if token and token.type in ('EQ', 'NE', 'LT', 'GT', 'LE', 'GE'):
            op_token = self.consume()
            right = self.parse_additive()
            return BinaryOp(op_token.value, left, right)
        
        return left
    
    def parse_additive(self) -> 'ASTNode':
        """Parse addition and subtraction."""
        left = self.parse_multiplicative()
        
        while self.current_token() and self.current_token().type in ('PLUS', 'MINUS'):
            op_token = self.consume()
            right = self.parse_multiplicative()
            left = BinaryOp(op_token.value, left, right)
        
        return left
    
    def parse_multiplicative(self) -> 'ASTNode':
        """Parse multiplication and division."""
        left = self.parse_unary()
        
        while self.current_token() and self.current_token().type in ('MUL', 'DIV'):
            op_token = self.consume()
            right = self.parse_unary()
            left = BinaryOp(op_token.value, left, right)
        
        return left
    
    def parse_unary(self) -> 'ASTNode':
        """Parse unary operations (NOT)."""
        token = self.current_token()
        if token and token.type == 'NOT':
            self.consume('NOT')
            expr = self.parse_unary()
            return UnaryOp('!', expr)
        
        return self.parse_primary()
    
    def parse_primary(self) -> 'ASTNode':
        """Parse primary expressions (atoms and parentheses)."""
        token = self.current_token()
        
        if token is None:
            raise SyntaxError("Unexpected end of formula")
        
        # Parenthesized expression
        if token.type == 'LPAREN':
            self.consume('LPAREN')
            expr = self.parse_or()
            self.consume('RPAREN')
            return expr
        
        # Indicator with shift: indicator[shift]
        if token.type == 'INDICATOR':
            match = re.match(r'([a-z_][a-z0-9_]*)\[(-?\d+)\]', token.value)
            if match:
                self.consume('INDICATOR')
                indicator = match.group(1)
                shift = int(match.group(2))
                return Indicator(indicator, shift)
        
        # Number
        if token.type == 'NUMBER':
            self.consume('NUMBER')
            return Literal(float(token.value))
        
        # Variable name (column reference)
        if token.type == 'NAME':
            self.consume('NAME')
            return Variable(token.value)
        
        raise SyntaxError(f"Unexpected token: {token}")


# ============================================================================
# AST Nodes
# ============================================================================

class ASTNode:
    """Base class for AST nodes."""
    
    def evaluate(self, data: Union[dict, pd.DataFrame]) -> Any:
        raise NotImplementedError


class Literal(ASTNode):
    """Numeric literal."""
    
    def __init__(self, value: float):
        self.value = value
    
    def evaluate(self, data: Union[dict, pd.DataFrame]) -> float:
        return self.value


class Variable(ASTNode):
    """Column reference (current bar)."""
    
    def __init__(self, name: str):
        self.name = name
    
    def evaluate(self, data: Union[dict, pd.DataFrame]) -> Any:
        if isinstance(data, dict):
            if self.name not in data:
                raise KeyError(f"Column '{self.name}' not found")
            return data[self.name]
        else:  # DataFrame
            if self.name not in data.columns:
                raise KeyError(f"Column '{self.name}' not found")
            # Return last value (most recent bar, since data is newest-first)
            return data[self.name].iloc[0]


class Indicator(ASTNode):
    """Indicator with shift: indicator[shift]."""
    
    def __init__(self, name: str, shift: int):
        self.name = name
        self.shift = shift  # 0=current, -1=previous, -2=2 bars ago
    
    def evaluate(self, data: Union[dict, pd.DataFrame]) -> Any:
        if isinstance(data, dict):
            # For dict, only shift 0 is supported
            if self.shift != 0:
                raise ValueError(f"Shift notation [{self.shift}] not supported for dict data")
            if self.name not in data:
                raise KeyError(f"Indicator '{self.name}' not found")
            return data[self.name]
        else:  # DataFrame
            if self.name not in data.columns:
                raise KeyError(f"Indicator '{self.name}' not found")
            
            # Data is sorted newest-first (index 0 = most recent)
            # shift 0 = current bar (index 0)
            # shift -1 = previous bar (index 1)
            # shift -2 = 2 bars ago (index 2)
            idx = abs(self.shift)
            if idx >= len(data):
                raise ValueError(f"Not enough data for shift [{self.shift}]")
            
            return data[self.name].iloc[idx]


class BinaryOp(ASTNode):
    """Binary operation."""
    
    def __init__(self, op: str, left: ASTNode, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right
    
    def evaluate(self, data: Union[dict, pd.DataFrame]) -> Any:
        left_val = self.left.evaluate(data)
        right_val = self.right.evaluate(data)
        
        # Handle Series operations
        if isinstance(left_val, pd.Series) or isinstance(right_val, pd.Series):
            return self._eval_series(left_val, right_val)
        
        # Scalar operations
        if self.op == '&&':
            return bool(left_val) and bool(right_val)
        elif self.op == '||':
            return bool(left_val) or bool(right_val)
        elif self.op == '==':
            return left_val == right_val
        elif self.op == '!=':
            return left_val != right_val
        elif self.op == '<':
            return left_val < right_val
        elif self.op == '>':
            return left_val > right_val
        elif self.op == '<=':
            return left_val <= right_val
        elif self.op == '>=':
            return left_val >= right_val
        elif self.op == '+':
            return left_val + right_val
        elif self.op == '-':
            return left_val - right_val
        elif self.op == '*':
            return left_val * right_val
        elif self.op == '/':
            if right_val == 0:
                raise ValueError("Division by zero")
            return left_val / right_val
        else:
            raise ValueError(f"Unknown operator: {self.op}")
    
    def _eval_series(self, left_val: Any, right_val: Any) -> Any:
        """Handle Series operations."""
        # Convert scalars to Series if needed
        if not isinstance(left_val, pd.Series):
            left_val = pd.Series([left_val] * len(right_val if isinstance(right_val, pd.Series) else [left_val]))
        if not isinstance(right_val, pd.Series):
            right_val = pd.Series([right_val] * len(left_val))
        
        # Comparison operators return boolean Series
        if self.op == '==':
            return (left_val == right_val).iloc[0]  # Return scalar bool
        elif self.op == '!=':
            return (left_val != right_val).iloc[0]
        elif self.op == '<':
            return (left_val < right_val).iloc[0]
        elif self.op == '>':
            return (left_val > right_val).iloc[0]
        elif self.op == '<=':
            return (left_val <= right_val).iloc[0]
        elif self.op == '>=':
            return (left_val >= right_val).iloc[0]
        
        # Logical operators
        elif self.op == '&&':
            left_bool = (left_val != 0).iloc[0] if isinstance(left_val, pd.Series) else bool(left_val)
            right_bool = (right_val != 0).iloc[0] if isinstance(right_val, pd.Series) else bool(right_val)
            return left_bool and right_bool
        elif self.op == '||':
            left_bool = (left_val != 0).iloc[0] if isinstance(left_val, pd.Series) else bool(left_val)
            right_bool = (right_val != 0).iloc[0] if isinstance(right_val, pd.Series) else bool(right_val)
            return left_bool or right_bool
        
        # Arithmetic operators
        elif self.op == '+':
            return (left_val + right_val).iloc[0]
        elif self.op == '-':
            return (left_val - right_val).iloc[0]
        elif self.op == '*':
            return (left_val * right_val).iloc[0]
        elif self.op == '/':
            return (left_val / right_val).iloc[0]
        
        else:
            raise ValueError(f"Unknown operator: {self.op}")


class UnaryOp(ASTNode):
    """Unary operation."""
    
    def __init__(self, op: str, expr: ASTNode):
        self.op = op
        self.expr = expr
    
    def evaluate(self, data: Union[dict, pd.DataFrame]) -> Any:
        val = self.expr.evaluate(data)
        
        if self.op == '!':
            return not bool(val)
        else:
            raise ValueError(f"Unknown unary operator: {self.op}")


def parse_formula(formula: str) -> ASTNode:
    """Parse a DSL formula into an AST."""
    lexer = Lexer(formula)
    parser = Parser(lexer.get_tokens())
    return parser.parse()


def evaluate_dsl(formula: str, data: Union[dict, pd.DataFrame]) -> bool:
    """Parse and evaluate a DSL formula."""
    ast = parse_formula(formula)
    result = ast.evaluate(data)
    return bool(result)
