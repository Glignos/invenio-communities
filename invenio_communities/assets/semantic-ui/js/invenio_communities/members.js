/*
 * This file is part of Invenio.
 * Copyright (C) 2017-2020 CERN.
 *
 * Invenio is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */
import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import { Formik, Form, FieldArray, Field } from "formik";
import * as Yup from "yup";
import axios from "axios";
import _ from "lodash";
import { Dropdown } from 'semantic-ui-react'
import { TextField, SelectField } from 'react-invenio-forms';


const COMMUNITY_ROLES = [
  { id: "admin", display: "Administrator" },
  { id: "curator", display: "Curator" },
  { id: "member", display: "Member" },
];


const CommunityMembers = () => {
  const [globalError, setGlobalError] = useState(null);
  const [requestSuccess, setRequestSuccess] = useState(null);
  const [communityMembers, setCommunityMembers] = useState(null);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [communityRequests, setCommunityRequests] = useState(false);
  const [activeTab, setActiveTab] = useState('members');
  const [showOutgoingRequests, setShowOutgoingRequests] = useState(false);
  const [pageAccess, setPageAccess] = useState(false);


  var communityID = window.location.pathname.split('/')[2];

  var removeMembership = (membershipID) => {
    axios
      .delete(`/api/communities/${communityID}/members/requests/${membershipID}`)
      .then(response => {
        setRequestSuccess(true)
      })
      .catch(error => {
        // TODO: handle nested fields
        if (error) {
          setGlobalError(error)
        }
        console.log(error.response.data);
      })
  }


  var manageRequest = (membershipID, role, action, message=null) => {
    console.log(communityRequests)
    var payload = { 'role': role}
    if (message){
      payload['message'] = message;
    }
    axios
      .post(`/api/communities/${communityID}/members/requests/${membershipID}/${action}`,
        payload)
      .then(response => {
        setRequestSuccess(true)
      })
      .catch(error => {
        // TODO: handle nested fields
        if (error) {
          setGlobalError(error)
        }
        console.log(error.response.data);
      })
  }


  var modifyMembership = (membershipID, role) => {
    console.log(communityRequests)
    var payload = { 'role': role }
    axios
      .put(`/api/communities/${communityID}/members/requests/${membershipID}`,
        payload)
      .then(response => {
        setRequestSuccess(true)
      })
      .catch(error => {
        // TODO: handle nested fields
        if (error) {
          setGlobalError(error)
        }
        console.log(error.response.data);
      })
  }

  // var removeMember = (userID) => {
  //   axios
  //   .delete(`/api/communities/${communityID}/requests/members/${membershipID}`)
  //   .then(response => {
  //     setRequestSuccess(true)
  //   })
  //   .catch(error => {
  //     // TODO: handle nested fields
  //     if (error) {
  //       setGlobalError(error)
  //     }
  //     console.log(error.response.data);
  //   })
  // }

  // var editMemberRole = (userID, role) => {
  //   var payload = {'user_id': userID, 'role': role}
  //   axios
  //   .put(`/api/communities/${communityID}/members`, payload)
  //   .then(response => {
  //     setRequestSuccess(true)
  //   })
  //   .catch(error => {
  //     // TODO: handle nested fields
  //     if (error) {
  //       setGlobalError(error)
  //     }
  //     console.log(error.response.data);
  //   })
  // }

  var joinCommunity = () => {
    var payload = { 'request_type': 'request' }
    axios.
      post(`/api/communities/${communityID}/members`, payload)
      .then(response => {
        setRequestSuccess(true)
      })
      .catch(error => {
        // TODO: handle nested fields
        if (error) {
          setGlobalError(error)
        }
        console.log(error.response.data);
      })
  }

  var displayMembers = () => {
    setCommunityMembers(null)
    fetchAndSetMemberships('A')
    setActiveTab('members')
  }

  var displayRequests = () => {
    setCommunityMembers(null)
    fetchAndSetMemberships('P', true)
    setActiveTab('requests')
  }

  var displayRejectedRequests = () => {
    setCommunityMembers(null)
    setActiveTab('rejected')
    fetchAndSetMemberships('R', true)
  }

  var fetchAndSetMemberships = (status, include_requests = false) => {
    fetch(`/api/communities/${communityID}/members?status=${status}&include_requests=${include_requests}`)
      .then(res => {
        if (res.status === 200) {
          setPageAccess(true)
        }
        return res.json();
      })
      .then(
        (result) => {
          setCommunityMembers(result);
        },
        (error) => {
        }
      )
  }

  useEffect(() => {
    fetchAndSetMemberships('A')
    // fetch(`/api/communities/${communityID}/members/requests`)
    //   .then(res => {
    //     if(res.status === 200){
    //       setPageAccess(true);
    //     }
    //   return res.json();
    // })
    //   .then(
    //     (result) => {
    //         setCommunityRequests(result);
    //     },
    //     (error) => {
    //     }
    //   )
  }, [])
  if (!communityMembers) {
    return ('Give us just a second.');
  }
  else if (!pageAccess) {
    return (
      <button type="button" onClick={joinCommunity}>Join this community</button>
    )
  }
  else {
    return (
      <div class="container ui">
        <div class="ui top secondary pointing menu">
          <a class="active item" onClick={displayMembers}>Members</a>
          <a class="item" onClick={displayRequests}>Pending Requests</a>
          <a class="item" onClick={displayRejectedRequests}>Rejected Requests</a>
        </div>
        {(() => {
          switch (activeTab) {
            case 'members':
              return <div>
                <h1>Community members</h1>
                <table class="ui celled table">
                  <thead>
                    <tr>
                      <th>Username</th>
                      <th>Role</th>
                      <th>Remove Member</th>
                    </tr>
                  </thead>
                  <tbody>
                    {communityMembers.hits.hits.accepted.map((member, index) => (
                      <tr key={index}>
                        <td>{member.username}</td>
                        <td>
                          <select defaultValue={member.role}
                            onChange={(event) => member.role = event.target.value}>
                            {COMMUNITY_ROLES.map(choice => (
                              <option key={choice.id} value={choice.id}>
                                {choice.display}
                              </option>
                            ))}
                          </select>
                          <button onClick={() => modifyMembership(member.id, member.role)}><i class="ui check icon"></i></button>
                        </td>
                        <td><button onClick={() => removeMembership(member.id)}><i class="ui ban icon"></i></button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            case 'requests':
              return <div>
                <h1>Community member requests</h1>
                <table class="ui celled table">
                  <thead>
                    <tr>
                      <th>Username or Email</th>
                      <th>Role</th>
                      <th>Request Type</th>
                      <th>Comments</th>
                      <th>Accept</th>
                      <th>Reject</th>
                    </tr>
                  </thead>
                  <tbody>
                    {communityMembers.hits.hits.pending.map((member, index) => (
                      <tr key={index}>
                        <td>{member.username || member.email || member.user_id}</td>
                        <td>
                          <select defaultValue={member.role}
                            onChange={(event) => member.role = event.target.value}>
                            {COMMUNITY_ROLES.map(choice => (
                              <option key={choice.id} value={choice.id}>
                                {choice.display}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>{member.request.request_type}</td>
                        <td>{member.request.comments.map((comment, index) => (
                          <p key={index}>{comment.message}</p>))}</td>
                        <td><button onClick={() => manageRequest(member.id, member.role, 'accept')}><i class="ui check icon"></i></button></td>
                        <td><button onClick={() => manageRequest(member.id, member.role, 'reject')}><i class="ui ban icon"></i></button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            case 'rejected':
              return <div>
                <h1>Community members</h1>
                <table class="ui celled table">
                  <thead>
                    <tr>
                      <th>Username or Email</th>
                      <th>Comments</th>
                    </tr>
                  </thead>
                  <tbody>
                    {communityMembers.hits.hits.rejected.map((member, index) => (
                      <tr key={index}>
                        <td>{member.username || member.email || member.user_id}</td>
                        <td>{member.request.comments.map((comment, index) => (
                          <p>{comment.message}</p>))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
          }
        })()}
      </div>
    )
    {/* <h3>Outgoing Community Requests ({communityRequests.out_count})</h3>
        {showOutgoingRequests ? (
          <div className="container">
          <button type="button" onClick={displayOutgoingRequests}>-</button>
          {communityRequests.hits.hits.pending.invitations.map( (request, index) => {
            request.role = COMMUNITY_ROLES_TO_ID[request.role]
            console.log(request.role)
            return (
            <div key={index}>
              <li>User email: {request.email}</li>
              <label>Invited as:</label>
              <select className="form-control" defaultValue={request.role}
               onChange={(event) => request.role=event.target.value}>
                {COMMUNITY_ROLES.map(choice =>(
                    <option key={choice.id} value={choice.id}>
                      {choice.display}
                    </option>
                ))}
                </select>
              <button type="button" onClick={() => modifyMembership(request.id, request.role)}>Modify role</button>
              <button type="button" onClick={() => removeMembership(request.id)}>Cancel request</button>
            </div>
          )})}
          </div>
        ) : (
          <button type="button" onClick={displayOutgoingRequests}>+</button>
        ) }
        <h3>Incoming Community Requests ({communityRequests.inc_count})</h3> */}
    {/* {showIncomingRequests ? (
          <div className="container">
          <button type="button" onClick={displayIncomingRequests}>-</button>
          {communityRequests.hits.hits.pending.requests.map( (request, index) => {
            let role = 'M';
            return (<div key={index}>
              <li>User email: {request.email}</li>
              <div className="form-group">
              <label>Role:</label>
              <select className="form-control" defaultValue='M'
               onChange={(event) => role=event.target.value}>
                {COMMUNITY_ROLES.map(choice =>(
                    <option key={choice.id} value={choice.id}>
                      {choice.display}
                    </option>
                ))}
                </select>
                </div>
                <button type="button" onClick={() => manageRequest(request.req_id, role, 'accept')}>Accept request</button>
                <button type="button" onClick={() => manageRequest(request.req_id, role, 'decline')}>Decline request</button>
            </div>
          )})}
          </div>
        ) : (
          <button type="button" onClick={displayIncomingRequests}>+</button>
        ) } */}
    {/* <button type="button" onClick={displayInviteForm}>{!showInviteForm ? 'Invite a member': 'See the community members'}</button> */ }
    {/* {activeTab=='members' ? (

            ) : (
            <div className="form-group">
            <h1>Invite a member</h1>
            <Formik
              initialValues={{
                email: "",
                role: "C",
                request_type: "invitation"
              }}
              validationSchema={Yup.object({
                email: Yup.string()
                  .required("Required"),
                role: Yup.string()
                  .required("Required")
                  .oneOf(
                    COMMUNITY_ROLES.map(c => {
                      return c.id;
                    })
                  ),
              })}
              onSubmit={(values, { setSubmitting, setErrors, setFieldError }) => {
                setSubmitting(true);
                const payload = _.pickBy(values, val => val !== "" && !_.isNil(val));
                var communityID = window.location.pathname.split('/')[2];
                axios
                  .post(`/api/communities/${communityID}/members`, payload)
                  .then(response => {
                    console.log(response);
                  })
                  .catch(error => {
                    // TODO: handle nested fields
                    if (error.response.data.errors) {
                      error.response.data.errors.map(({ field, message }) =>
                        setFieldError(field, message)
                      );
                    } else if (error.response.data.message) {
                      setGlobalError(error.response.data.message);
                    }
                    console.log(error.response.data);
                  })
                  .finally(() => setSubmitting(false));
              }} >
              {({ values, isSubmitting, isValid }) => (
                <Form>
                  <TextField label="email" placeholder="example@email.com" name="email" />
                  <SelectField choices={COMMUNITY_ROLES} label="Role" name="role" />
                  <button
                    disabled={!isValid || isSubmitting}
                    className="btn"
                    type="submit"
                  >
                    Submit
                    </button>
                  {globalError ? (
                    <div className="help-block">{globalError}</div>
                  ) : null}
                </Form>
              )}
            </Formik>
          </div>
      )} */}

  }
}


ReactDOM.render(<CommunityMembers />, document.getElementById("app"));

export default CommunityMembers;
