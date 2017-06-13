import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import Pusher from 'pusher-js';

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
    this.state = {
      game: {},
      seats: this.initializeSeats(),
      user: null
    }
    // This binding is necessary to make `this` work in the callback
    this.login = this.login.bind(this);
    this.sit = this.sit.bind(this);
    this.bet = this.bet.bind(this);
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
          user: data.user,
          game: data.game,
          seats: this.handleSeatChange(data.seats, data.user)
      });

      // subscribe to the current game's channel
      this.channel = this.pusher.subscribe("channel" + data.game.gameId);
      this.channel.bind('updateState', function(state) {
        this.setState({
          game: state.game,
          seats: this.handleSeatChange(state.seats, data.user)
        });
      }, this);
    }).catch(error => {console.log(error)});
  }

  handleSeatChange(newSeats, user) {
    const defaultSeats = this.initializeSeats();
    const seats = Object.assign(defaultSeats, newSeats);
    const currentSeatId = Object.keys(seats).find(seatId => seats[seatId].userId == user.userId);
    if (currentSeatId) {
      seats[currentSeatId].isCurrentUser = true;
      Object.keys(seats).forEach(seatId => {
        seats[seatId].isSeatAvailable = false;
      });
    }
    return seats;
  }

  initializeSeats() {
    const seats = {};
    for (let i = 0; i < 9; i++) {
      seats[i] = {
        seatNumber: i,
        chip: 0,
        user: null,
        action: null,
        hand: [],
        isSeatAvailable: true
      };
    }
    return seats;
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
  bet(seatId, betSize) {
    const body = JSON.stringify({
      userId: this.state.user.userId,
      seatId: seatId,
      bet: betSize
    });
    fetch("/bet", {method: 'POST', body: body}).catch(error => {console.log(error)});
  }

  render() {
    const seats = Object.keys(this.state.seats).map(seatNumber => 
      <Seat key={seatNumber} {...this.state.seats[seatNumber]} sit={this.sit} bet={this.bet} />
    );
    return (
      <div className="App">
        <div className="App-header">
          <h2>Welcome to AWESOME POKER!</h2>
        </div>
        {this.state.user ? 
        <div className="board">
          <Game {...this.state.game} />
          {seats}
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
      <li key={index}>{card} </li>
    );
    return (
      <div>
        <h3> {"POT: " + this.props.pot}  </h3>
        <ul>
          {cards}
        </ul>
      </div>
    )
  }
}

class Seat extends Component {
  constructor(props) {
    super(props);
    this.state = {
      betSize: 6
    };
    this.sit = this.sit.bind(this);
    this.fold = this.fold.bind(this);
    this.check = this.check.bind(this);
    this.call = this.call.bind(this);
    this.bet = this.bet.bind(this);
    this.changeBetSize = this.changeBetSize.bind(this);
  }

  sit() {
    this.props.sit(this.props.seatNumber);
  }

  fold() {
    this.props.bet(this.props.seatId, -1);
  }

  check() {
    this.props.bet(this.props.seatId, 0);
  }
  
  call() {
    // TODO
  }

  bet() {
    this.props.bet(this.props.seatId, this.state.betSize);
  }

  changeBetSize(e) {
    this.setState({
      betSize: e.target.value
    });
  }

  render() {
    return (
      <div className="seat">
        <label>Seat {this.props.seatNumber}</label>
        {this.props.username &&
        <div>
          <span> {"username: " + this.props.username} </span>
          <span> {"chips: " + this.props.chip} </span>
          <span> {"bet: " + this.props.status} </span>
          {this.props.isCurrentUser && 
          <span>
            <button onClick={this.fold}> FOLD </button>
            <button onClick={this.check}> CHECK </button>
            <button onClick={this.call}> CALL </button>
            <button onClick={this.bet}> BET </button>
            <input type="text" value={this.state.betSize} onChange={this.changeBetSize} />
          </span>
          }
          <ul>
            {this.props.hand.map((card, index) =>
              <li key={index}>{card} </li>
            )}
          </ul>
        </div> }
        {this.props.isSeatAvailable &&
          <button onClick={this.sit}>Sit Down</button>
        }
      </div>
    )
  }
}

ReactDOM.render(<App />, document.getElementById('content'));
