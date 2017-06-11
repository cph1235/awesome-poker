import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import Pusher from 'pusher-js';

const SUITS = {
  DIAMONDS: "DIAMONDS",
  SPADES: "SPADES",
  CLUBS: "CLUBS",
  HEARTS: "HEARTS"
}

const CARDS = [
  "A",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "J",
  "Q",
  "K"
]

const STAGE = {
  WAIT: "WAIT",
  PREFLOP: "PREFLOP",
  FLOP: "FLOP",
  TURN: "TURN",
  RIVER: "RIVER",
  SHOWDOWN: "SHOWDOWN"
}

class App extends Component {
  constructor() {
    super();

    const seats = {};
    for (let i = 0; i < 9; i++) {
      seats[i] = {
        seatNumber: i,
        chip: 0,
        user: null,
        action: null,
        hand: []
      };
    }
    this.state = {
      game: {},
      seats: seats,
      user: null
    }
    // This binding is necessary to make `this` work in the callback
    this.sit = this.sit.bind(this);
    this.login = this.login.bind(this);
  }

  componentWillMount() {
    this.pusher = new Pusher('b62d17064a726aa724fe', {
      cluster: 'us2',
      encrypted: true
    });
  }

  // user login
  login(username, password, chip) {
    const body = JSON.stringify({
      username: username,
      password: password,
      chip: chip
    });
    
    fetch("/login", {method: 'post', body: body})
    .then(res => res.json())
    .then(data => {
      this.setState(prevState => {
        return {
          user: data.user,
          game: data.game,
          seats: Object.assign(prevState.seats, data.seats)
        };
      });

      // subscribe to the current game's channel
      this.channel = this.pusher.subscribe("channel" + data.game.gameId);
      this.channel.bind('updateState', function(state) {
        this.setState(prevState => {
          return {
            game: state.game,
            seats: Object.assign(prevState.seats, state.seats)
          };
        });
      }, this);
    }).catch(error => {console.log(error)});
  }

  // user sit down on a seat 
  sit(seatNumber) {
    const body = JSON.stringify({
      userId: this.state.user.userId,
      username: this.state.user.username,
      chip: this.state.user.chip,
      gameId: this.state.game.gameId,
      seatNumber: seatNumber
    });
    fetch("/sit", {method: 'POST', body: body});
  }

  // user makes a bet
  bet(e) {
    const body = JSON.stringify({
      userId: this.state.user.userId,
      amount: e.target.size
    });
    fetch("/bet",{method: 'POST', body: body})
    .then(res => res.json())
    .then(data => {

    });
  }

  render() {
    const seats = Object.keys(this.state.seats).map(seatNumber => 
      <Seat key={seatNumber} {...this.state.seats[seatNumber]} sit={this.sit} />
    );
    return (
      <div className="App">
        <div className="App-header">
          <h2>Welcome to AWESOME POKER!</h2>
        </div>
        {this.state.user ? 
        <div className="board">
          <Game board={this.state.game.board} />
          {seats}
          <button size="-1" onClick={this.check}> CHECK </button>
          <button size="0" onClick={this.check}> CHECK </button>
          <button size="2" onClick={this.call}> CALL </button>
          <button size="6" onClick={this.bet}> BET </button>
        </div>
        : <LoginDialog login={this.login} />}
      </div>
    );
  }
}

class LoginDialog extends Component {
  constructor(props) {
    super(props);
    this.state = {
      username: "",
      password: "",
      chip: 200
    }
    this.submit = this.submit.bind(this);
    this.handleChange = this.handleChange.bind(this);
  }

  submit(e) {
    e.preventDefault();
    if (!this.state.username || !this.state.password) {
      alert("Username and password can't be empty");
      return;
    }
    if (!Number.isInteger(this.state.chip)) {
      alert("chips must be numeric");
      return;
    }
    this.props.login(this.state.username, this.state.password, this.state.chip);
  }

  handleChange(e) {
    const newState = {};
    newState[e.target.name] = e.target.value;
    this.setState(newState);
  }

  render() {
    return (
      <form className="loginDialog" onSubmit={this.submit}>
        <label>username: </label>
        <input type="text" name="username" value={this.state.username} onChange={this.handleChange} />
        <label>password: </label>
        <input type="text" name="password" value={this.state.password} onChange={this.handleChange} />
        <label>chips: </label>
        <input type="text" name="chip" value={this.state.chip} onChange={this.handleChange}/>
        <input type="submit" value="Submit" />
      </form>
    );
  }
}

class Game extends Component {
  render() {
    const cards = this.props.board.map((card, index) =>
      <li key={index}>{card.suit + " " + card.value} </li>
    );
    return (
      <ul>
        <li>Board</li>
        {cards}
      </ul>
    )
  }
}

class Seat extends Component {
  constructor(props) {
    super(props);

    this.sit = this.sit.bind(this);
  }

  sit() {
    this.props.sit(this.props.seatNumber);
  }

  render() {
    return (
      <div className="seat">
        <label>Seat {this.props.seatNumber}</label>
        {this.props.username ? 
        <div>
          <span> {"username: " + this.props.username} </span>
          <span> {"chips: " + this.props.chip} </span>
          <ul>
            {this.props.hand.map((card, index) =>
              <li key={index}>{card.suit + " " + card.value} </li>
            )}
          </ul>
        </div> :
        <button onClick={this.sit}>Sit Down</button>}
      </div>
    )
  }
}

ReactDOM.render(<App />, document.getElementById('content'));
