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

    const seats = [];
    for (let i = 0; i < 9; i++) {
      seats.push({
        seatNumber: i,
        chip: 0,
        user: null,
        action: false
      });
    }
    this.state = {
      board: [],
      stage: STAGE.WAIT,
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
      this.setState({
        user: {userId: data.userId, username: data.username, chip: data.chip},
        game: data.gameId
      });

      // subscribe to the current game's chanel
      this.channel = this.pusher.subscribe(data.gameId);
      this.channel.bind('updateState', function(message) {
        this.setState(message);
      }, this);
    }).catch(error => {console.log(error)});
  }

  // user sit down on a seat 
  sit(seat) {
    const body = {
      gameId: this.state.gameId,
      seat: 0
    };
    fetch("/sit", {method: 'POST', body: body})
    .then(res => res.json())
    .then(data => {
      this.channel = this.pusher.subscribe(data.gameId + data.seatId);
      this.channel.bind('action', function(message) {
        console.log(message);
      }, this);
    });
  }

  // user makes a bet
  bet(amount) {
    fetch("/bet",{method: 'POST', body: {amount: ammount}})
    .then(res => res.json())
    .then(data => {

    });
  }

  render() {
    const seats = this.state.seats.map(seat => 
      <Seat key={seat.seatNumber} seat={seat} sit={this.sit} />
    );
    return (
      <div className="App">
        <div className="App-header">
          <h2>Welcome to AWESOME POKER!</h2>
        </div>
        {this.state.user ? 
        <div className="board">
          <Game cards={this.state.board} />
          {seats}
          <button onClick={this.check}> CHECK </button>
          <button onClick={this.call}> CALL </button>
          <button onClick={this.bet}> BET </button>
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
    const cards = this.props.cards.map((card, index) =>
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
        <label>Seat {this.props.seat.seatNumber}</label>
        {this.props.seat.user ? 
        <div>
          <span> {this.props.seat.user.username} </span>
          <span> {this.props.seat.chip} </span>
        </div> :
        <button onClick={this.sit}>Sit Down</button>}
      </div>
    )
  }
}

ReactDOM.render(<App />, document.getElementById('content'));
