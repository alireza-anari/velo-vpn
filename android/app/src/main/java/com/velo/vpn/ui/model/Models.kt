package com.velo.vpn.ui.model

data class Plan(val title: String, val price: String, val recommended: Boolean = false)
data class Server(val country: String, val flag: String, val ping: Int? = null, val premium: Boolean = false, val vip: Boolean = false)
data class Mission(val title: String, val subtitle: String, val reward: Int, val progress: Int, val target: Int, val completed: Boolean = false)
data class InvitedFriend(val name: String, val status: String, val earnedHearts: Int, val day: Int? = null)
